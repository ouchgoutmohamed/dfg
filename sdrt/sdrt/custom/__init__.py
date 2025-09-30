"""Custom scripts and overrides for SDRT app.

Purchase Order customization: fetch items from Demande d'Achat (Material Request child table)
instead of Item master.
"""

import json
from typing import List, Dict, Optional
import frappe
from frappe import _
from frappe.utils import flt

__all__ = [
    'get_multi_da_budget_lines', 
    'engage_budgets_for_po', 
    'validate_purchase_order_item',
    'rollback_budgets_for_po',
    'update_sdr_budget_available',
    'get_default_supplier_query',
	'ensure_budget_item',
	# keep PR standard: no overrides exported
]


def _collect_da_lines(material_request: str) -> List[Dict]:
	"""Collect raw lines from a single Material Request custom child table.

	Kept internal so we can reuse for multi-selection.
	"""
	mr = frappe.get_doc('Material Request', material_request)
	rows: List[Dict] = []
	
	# Debug logging to understand what's happening
	frappe.log_error(f"DEBUG: Material Request {material_request} has demande_dachat table: {bool(mr.get('demande_dachat'))}", "DA Debug")
	demande_dachat_data = mr.get('demande_dachat') or []
	frappe.log_error(f"DEBUG: demande_dachat data length: {len(demande_dachat_data)}", "DA Debug")
	
	# Get a valid UOM that exists in the system
	def get_valid_uom():
		preferred = ['Nos', 'Unit', 'Unité', 'PCE', 'Each']
		for uom in preferred:
			if frappe.db.exists('UOM', uom):
				return uom
		# Fallback to first UOM found
		return frappe.db.get_value('UOM', {}, 'name') or 'Nos'
	
	valid_uom = get_valid_uom()
	
	for r in demande_dachat_data:
		frappe.log_error(f"DEBUG: Processing line with code: {getattr(r, 'code_analytique', 'None')}", "DA Debug")
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
	
	frappe.log_error(f"DEBUG: Final rows count: {len(rows)}", "DA Debug")
	return rows


def _aggregate_amounts(rows: List[Dict]) -> Dict[str, float]:
	"""Return aggregated amount (qty*rate) per budget code."""
	agg: Dict[str, float] = {}
	for r in rows:
		code = r.get('code_analytique')
		if not code:
			continue
		amt = flt(r.get('qty')) * flt(r.get('rate'))
		agg[code] = agg.get(code, 0) + amt
	return agg


def _validate_budget(purchase_order: Optional[str], new_rows: List[Dict]):
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
def get_da_budget_lines(material_request: str, supplier: Optional[str] = None, purchase_order: Optional[str] = None):
	"""Single Material Request import with budget validation."""
	if not material_request:
		frappe.throw(_('Material Request manquant.'))
	
	frappe.log_error(f"DEBUG: get_da_budget_lines called with MR: {material_request}", "DA Debug")
	rows = _collect_da_lines(material_request)
	frappe.log_error(f"DEBUG: get_da_budget_lines returned {len(rows)} rows", "DA Debug")
	
	if not rows:
		frappe.log_error(f"DEBUG: No rows found for Material Request {material_request}. Check if demande_dachat table has data.", "DA Debug")
	
	_validate_budget(purchase_order, rows)
	return rows


@frappe.whitelist()
def get_multi_da_budget_lines(material_requests: str, supplier: Optional[str] = None, purchase_order: Optional[str] = None):
	"""Collect lines from multiple Material Requests and validate budgets.

	`material_requests` can be a JSON array string or comma separated names.
	"""
	if not material_requests:
		frappe.throw(_('Veuillez sélectionner au moins une Demande de Matériel.'))
	
	frappe.log_error(f"DEBUG: get_multi_da_budget_lines called with: {material_requests}", "DA Debug")
	
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

	frappe.log_error(f"DEBUG: Processing MR list: {mr_list}", "DA Debug")

	all_rows: List[Dict] = []
	for mr in mr_list:
		frappe.log_error(f"DEBUG: Processing MR: {mr}", "DA Debug")
		rows = _collect_da_lines(mr)
		frappe.log_error(f"DEBUG: MR {mr} returned {len(rows)} rows", "DA Debug")
		all_rows.extend(rows)

	frappe.log_error(f"DEBUG: Total rows collected: {len(all_rows)}", "DA Debug")
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

## Purchase Receipt: keep ERPNext standard; no custom mapping or field sync.
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


def _ensure_budget_item_exists(code: str, description: str | None = None):
	"""Ensure an Item with code `code` exists; create it with safe defaults if missing.

	Returns the code back (useful for chaining).
	"""
	code = (code or '').strip()
	if not code:
		return code
	if frappe.db.exists('Item', code):
		return code

	# Safe defaults matching ERPNext expectations
	stock_uom = 'Nos'
	item_group = 'All Item Groups' if frappe.db.exists('Item Group', 'All Item Groups') else (frappe.db.get_value('Item Group', {}, 'name') or 'All Item Groups')

	# Create minimal non-stock, purchasable item
	try:
		frappe.get_doc({
			'doctype': 'Item',
			'item_code': code,
			'item_name': (description or code)[:140],
			'description': (description or code)[:1000],
			'item_group': item_group,
			'stock_uom': stock_uom,
			'is_stock_item': 0,
			'is_sales_item': 0,
			'is_purchase_item': 1
		}).insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		pass
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Auto-create Item failed for budget code {code}")
	return code


def validate_purchase_order_item(doc, method):
	"""Server guardrails for PO items:
	- If code_analytique is given, ensure an Item with the same code exists and is set.
	- Prevent numeric-only item_code like "1"; replace with code_analytique if available.
	"""
	for item in (doc.items or []):
		code = (getattr(item, 'code_analytique', '') or '').strip()
		item_code = (getattr(item, 'item_code', '') or '').strip()

		# If user typed a numeric code (e.g., "1"), reset to budget code when available
		if item_code and item_code.isdigit() and code:
			item.item_code = code
			item_code = code

		# If we have a budget code, ensure the matching Item exists and is used
		if code:
			_ensure_budget_item_exists(code, getattr(item, 'item_name', None) or getattr(item, 'description', None))
			item.item_code = code

		# Ensure minimal UOM fields to pass standard validations
		if not getattr(item, 'uom', None):
			item.uom = 'Nos'
		if not getattr(item, 'stock_uom', None):
			item.stock_uom = item.uom or 'Nos'


@frappe.whitelist()
def ensure_budget_item(code: str, description: Optional[str] | None = None):
	"""Whitelisted helper to ensure an Item exists for the given budget code.

	Inputs:
	- code: budget analytic code to use as Item.item_code
	- description: optional description to use for Item.item_name/description

	Returns:
	- dict with keys { item_code, stock_uom, item_name }
	"""
	if not code:
		return {}
	created_code = _ensure_budget_item_exists(code, description)
	if not created_code:
		return {}
	stock_uom, item_name = frappe.db.get_value('Item', created_code, ['stock_uom', 'item_name']) or ('Nos', created_code)
	return {"item_code": created_code, "stock_uom": stock_uom or 'Nos', "item_name": item_name or created_code}


def ensure_no_default_item_code_on_pr():
	"""System migration safety: remove default '1' on Purchase Receipt Item.item_code.

	In some ERPNext builds, the child field comes with default=1 and hidden=1,
	which causes new rows to get item_code=1 and then fail in pricing logic.
	We enforce default to be empty via a Property Setter.
	"""
	try:
		# Check current default
		df = frappe.db.get_value(
			"DocField",
			{"parent": "Purchase Receipt Item", "fieldname": "item_code"},
			["default"], as_dict=True
		)
		current = (df.default if df else None) or ""
		if current == "1":
			# Create or update Property Setter to clear default
			name = "Purchase Receipt Item-item_code-default"
			if frappe.db.exists("Property Setter", name):
				ps = frappe.get_doc("Property Setter", name)
				ps.value = ""
				ps.save(ignore_permissions=True)
			else:
				frappe.get_doc({
					"doctype": "Property Setter",
					"name": name,
					"doc_type": "Purchase Receipt Item",
					"doctype_or_field": "DocField",
					"field_name": "item_code",
					"property": "default",
					"property_type": "Data",
					"value": "",
				}).insert(ignore_permissions=True)
			frappe.clear_cache(doctype="Purchase Receipt Item")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ensure_no_default_item_code_on_pr failed")


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


## Purchase Receipt validation removed to avoid conflicts with standard apply_price_list and mapping.

