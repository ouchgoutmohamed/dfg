"""Custom scripts and overrides for SDRT app.

Purchase Order customization: fetch items from Demande d'Achat (Material Request child table)
instead of Item master.
"""

import json
import frappe
from frappe import _
from frappe.utils import flt


def _collect_da_lines(material_request: str) -> list[dict]:
	"""Collect raw lines from a single Material Request custom child table.

	Kept internal so we can reuse for multi-selection.
	"""
	mr = frappe.get_doc('Material Request', material_request)
	rows: list[dict] = []
	
	# Get a valid UOM that exists in the system
	def get_valid_uom():
		preferred = ['Nos', 'Unit', 'Unité', 'PCE', 'Each']
		for uom in preferred:
			if frappe.db.exists('UOM', uom):
				return uom
		# Fallback to first UOM found
		return frappe.db.get_value('UOM', {}, 'name') or 'Nos'
	
	valid_uom = get_valid_uom()
	
	for r in mr.get('demande_dachat') or []:
		qty = flt(r.qte) if r.qte else 0
		unit_price = flt(r.pu) if r.pu else 0
		estimation = flt(getattr(r, 'estimation', 0))
		if not unit_price and estimation and qty:
			unit_price = estimation / qty
		rows.append({
			'code_analytique': r.code_analytique,
			'description': r.description or '',
			'qty': qty or 0,
			'rate': unit_price or 0,
			'uom': valid_uom,
			'schedule_date': getattr(mr, 'schedule_date', None) or getattr(mr, 'transaction_date', None)
		})
	return rows


def _aggregate_amounts(rows: list[dict]) -> dict[str, float]:
	"""Return aggregated amount (qty*rate) per budget code."""
	agg: dict[str, float] = {}
	for r in rows:
		code = r.get('code_analytique')
		if not code:
			continue
		amt = flt(r.get('qty')) * flt(r.get('rate'))
		agg[code] = agg.get(code, 0) + amt
	return agg


def _validate_budget(purchase_order: str | None, new_rows: list[dict]):
	"""Validate that adding new_rows won't exceed available budget.

	Rules:
	- For each code_analytique, compute existing draft PO amount (qty*rate for current items).
	- Sum new rows per code.
	- Compare (existing_draft + new_addition) <= available_amount field on SDR Budget.
	- If any exceed, raise frappe.ValidationError listing offending codes with remaining vs required.
	"""
	if not new_rows:
		return

	existing: dict[str, float] = {}
	if purchase_order:
		try:
			po = frappe.get_doc('Purchase Order', purchase_order)
			for it in po.get('items') or []:
				code = getattr(it, 'code_analytique', None)
				if not code:
					continue
				amt = flt(getattr(it, 'qty', 0)) * flt(getattr(it, 'rate', 0))
				existing[code] = existing.get(code, 0) + amt
		except Exception:
			pass  # If PO not found, ignore

	new_agg = _aggregate_amounts(new_rows)
	errors = []
	for code, add_amt in new_agg.items():
		try:
			bud = frappe.get_doc('SDR Budget', code)
		except frappe.DoesNotExistError:
			errors.append(_(f"Budget introuvable: {code}"))
			continue
		available = flt(getattr(bud, 'available_amount', 0))
		existing_amt = existing.get(code, 0)
		remaining_for_new = available - existing_amt
		if add_amt > remaining_for_new + 1e-9:  # tolerance
			errors.append(_(f"Code {code}: requis {add_amt:.2f} > disponible {remaining_for_new:.2f}"))

	if errors:
		frappe.throw('<br>'.join(errors), title=_('Dépassement budget'))


@frappe.whitelist()
def get_da_budget_lines(material_request: str, supplier: str | None = None, purchase_order: str | None = None):
	"""Single Material Request import with budget validation."""
	if not material_request:
		frappe.throw(_('Material Request manquant.'))
	rows = _collect_da_lines(material_request)
	_validate_budget(purchase_order, rows)
	return rows


@frappe.whitelist()
def get_multi_da_budget_lines(material_requests: str, supplier: str | None = None, purchase_order: str | None = None):
	"""Collect lines from multiple Material Requests and validate budgets.

	`material_requests` can be a JSON array string or comma separated names.
	"""
	if not material_requests:
		frappe.throw(_('Veuillez sélectionner au moins une Demande de Matériel.'))
	# Normalize input to list
	if isinstance(material_requests, str):
		try:
			if material_requests.strip().startswith('['):
				mr_list = json.loads(material_requests)
			else:
				mr_list = [m.strip() for m in material_requests.split(',') if m.strip()]
		except Exception:
			frappe.throw(_('Format invalide pour material_requests'))
	else:
		mr_list = material_requests

	all_rows: list[dict] = []
	for mr in mr_list:
		all_rows.extend(_collect_da_lines(mr))

	_validate_budget(purchase_order, all_rows)
	return all_rows


def _commit_budget(code_analytique: str, amount: float):
	"""Increment committed_amount on SDR Budget and recompute available_amount.

	Assumes SDR Budget has fields: montant (total), committed_amount, available_amount.
	"""
	if not code_analytique:
		return
	try:
		bud = frappe.get_doc("SDR Budget", code_analytique)
	except frappe.DoesNotExistError:
		return
	committed = flt(getattr(bud, "committed_amount", 0)) + flt(amount)
	bud.committed_amount = committed
	total = flt(getattr(bud, "montant", 0))
	bud.available_amount = total - committed
	bud.db_update()


def _rollback_budget(code_analytique: str, amount: float):
	"""Reverse (decrement) committed_amount by 'amount'.

	Prevents negative committed; recompute available.
	"""
	if not code_analytique or not amount:
		return
	try:
		bud = frappe.get_doc("SDR Budget", code_analytique)
	except frappe.DoesNotExistError:
		return
	committed = flt(getattr(bud, "committed_amount", 0)) - flt(amount)
	if committed < 0:
		committed = 0
	bud.committed_amount = committed
	total = flt(getattr(bud, "montant", 0))
	bud.available_amount = total - committed
	bud.db_update()


def engage_budgets_for_po(doc, method=None):
	"""Engage (commit) budgets for a draft or submitted Purchase Order by summing line amounts.

	This can be called after importing DA lines and on submit to ensure sync.
	Idempotence: we do not track reversals here; simplistic accumulate model.
	"""
	for item in doc.get("items") or []:
		code = getattr(item, "code_analytique", None)
		amount = flt(getattr(item, "amount", 0))
		if code and amount:
			_commit_budget(code, amount)


def rollback_budgets_for_po(doc, method=None):
	"""Rollback committed budgets when a PO is cancelled."""
	for item in doc.get("items") or []:
		code = getattr(item, "code_analytique", None)
		amount = flt(getattr(item, "amount", 0))
		if code and amount:
			_rollback_budget(code, amount)


def update_sdr_budget_available(doc, method=None):  # doc_events: before_insert, validate
	"""Ensure available_amount = montant - committed_amount (ou = montant à la création).

	Règles:
	- committed_amount null => 0
	- montant null => 0
	- Si committed > montant: erreur (cohérence)
	- available_amount recalculé systématiquement (même champs read_only côté UI)
	"""
	committed = flt(getattr(doc, "committed_amount", 0))
	total = flt(getattr(doc, "montant", 0))
	if committed < 0:
		committed = 0
	if committed > total:
		frappe.throw(_(f"Montant engagé ({committed}) dépasse le montant total ({total})."))
	doc.committed_amount = committed
	doc.available_amount = total - committed

@frappe.whitelist()
def engage_po_budgets(purchase_order: str):
	"""Wrapper function to maintain backward compatibility for whitelisted calls."""
	doc = frappe.get_doc("Purchase Order", purchase_order)
	engage_budgets_for_po(doc)
	return {"status": "ok"}


@frappe.whitelist()
def get_budget_placeholder_item():
	"""Return structured info for a generic non-stock Item used for budget-only PO lines.

	Best practice adjustments:
	- Pick an existing UOM: prefer one of ['Nos','Unit','Unité','PCE','Each'] else first UOM found.
	- Create item once with code 'BUDGET-LINE'.
	- Return dict { item_code, stock_uom } instead of raw string for better client logic.
	"""
	placeholder_code = 'BUDGET-LINE'
	# Determine suitable UOM
	preferred = ['Nos', 'Unit', 'Unité', 'PCE', 'Each']
	chosen_uom = None
	for cand in preferred:
		if frappe.db.exists('UOM', cand):
			chosen_uom = cand
			break
	if not chosen_uom:
		chosen_uom = frappe.db.get_value('UOM', {}, 'name') or 'Nos'

	if not frappe.db.exists('Item', placeholder_code):
		item_group = 'All Item Groups'
		if not frappe.db.exists('Item Group', item_group):
			first_group = frappe.db.get_value('Item Group', {}, 'name')
			if first_group:
				item_group = first_group or 'All Item Groups'
		doc = frappe.get_doc({
			'doctype': 'Item',
			'item_code': placeholder_code,
			'item_name': 'Budget Placeholder',
			'item_group': item_group,
			'include_item_in_manufacturing': 0,
			'is_stock_item': 0,
			'allow_alternative_item': 0,
			'has_batch_no': 0,
			'has_serial_no': 0,
			'has_variants': 0,
			'stock_uom': chosen_uom
		})
		doc.insert(ignore_permissions=True)
		return {'item_code': placeholder_code, 'stock_uom': chosen_uom}

	# If already exists, read its stock_uom
	stock_uom = frappe.db.get_value('Item', placeholder_code, 'stock_uom') or chosen_uom
	return {'item_code': placeholder_code, 'stock_uom': stock_uom}


def validate_purchase_order_item(doc, method):
	"""Custom validation for Purchase Order Item to bypass Item validation for budget lines."""
	for item in doc.items:
		# If item has code_analytique but no valid item_code, set a simple placeholder
		if item.code_analytique and (not item.item_code or item.item_code in [None, '', 'None']):
			# Set simple placeholder - no external dependencies
			item.item_code = 'BUDGET-LINE'
			
			# Ensure UOM is valid - use simple defaults
			if not item.uom:
				item.uom = 'Nos'
			if not item.stock_uom:
				item.stock_uom = 'Nos'
			
			# Ensure the BUDGET-LINE item exists
			if not frappe.db.exists('Item', 'BUDGET-LINE'):
				frappe.get_doc({
					'doctype': 'Item',
					'item_code': 'BUDGET-LINE',
					'item_name': 'Budget Placeholder',
					'item_group': 'All Item Groups',
					'stock_uom': 'Nos',
					'is_stock_item': 0
				}).insert(ignore_permissions=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_default_supplier_query(doctype, txt, searchfield, start, page_len, filters):
	"""Safe override of ERPNext Material Request supplier link query.

	Fixes edge case when Material Request has no items, which causes SQL `IN ()` error.
	Behavior:
	- If MR has items, delegate to core method for full behavior.
	- If MR has no items, return an empty result set safely.
	"""
	mr_name = None
	if isinstance(filters, dict):
		mr_name = filters.get("doc")
	# Defensive: filters can be a JSON string in some calls
	if not mr_name and isinstance(filters, str):
		try:
			data = frappe.parse_json(filters)
			mr_name = data.get("doc") if isinstance(data, dict) else None
		except Exception:
			mr_name = None

	if not mr_name:
		return []

	try:
		doc = frappe.get_doc("Material Request", mr_name)
	except Exception:
		return []

	# If there are no items on the standard child table, avoid calling core (would generate IN ())
	if not getattr(doc, "items", None):
		return []

	# Delegate to core implementation for normal path
	core = frappe.get_attr(
		"erpnext.stock.doctype.material_request.material_request.get_default_supplier_query"
	)
	return core(doctype, txt, searchfield, start, page_len, filters)

