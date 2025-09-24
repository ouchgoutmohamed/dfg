"""Custom scripts and overrides for SDRT app.

Purchase Order customization: fetch items from Demande d'Achat (Material Request child table)
instead of Item master.
"""

import json
from typing import List, Dict, Optional
import frappe
from frappe import _
from frappe.utils import flt

__all__ = ['get_multi_da_budget_lines', 'engage_budgets_for_po', 'disengage_budgets_for_po']


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


	def _map_by_po_item(doc):
		"""Build an index of Purchase Order Item by name for fast lookup.

		Supports both single and multiple Purchase Orders referenced by PR items.
		"""
		from frappe.utils import flt
		index: dict[str, dict] = {}
		po_cache: dict[str, any] = {}
		for it in getattr(doc, "items", []) or []:
			po = getattr(it, "purchase_order", None) or getattr(doc, "purchase_order", None)
			poi = getattr(it, "po_detail", None) or getattr(it, "purchase_order_item", None)
			if not po or not poi or poi in index:
				continue
			if po not in po_cache:
				try:
					po_cache[po] = frappe.get_doc("Purchase Order", po)
				except Exception:
					po_cache[po] = None
			po_doc = po_cache.get(po)
			if not po_doc:
				continue
			for po_it in po_doc.get("items") or []:
				name = getattr(po_it, "name", None)
				if name:
					index[name] = po_it
		return index


	def sync_pr_items_from_po(doc, method=None):
		"""Enrich Purchase Receipt Items with custom fields from linked Purchase Order Items.

		Minimal and safe: executed after the standard map; only copies custom fields and
		doesn't override core quantities, warehouses, prices, or dates.

		Fields copied (if present on PO Item):
		- code_analytique -> set on PR Item
		- description (custom) -> set on PR Item's item_name, if item_name currently equals
		  the budget code or placeholder label.
		"""
		if not getattr(doc, "items", None):
			return

		# Build a lookup of PO Item rows by name once
		poi_index = _map_by_po_item(doc)
		if not poi_index:
			return

		for it in doc.items:
			po_item_name = getattr(it, "po_detail", None) or getattr(it, "purchase_order_item", None)
			if not po_item_name:
				continue
			src = poi_index.get(po_item_name)
			if not src:
				continue

			# Copy code_analytique if defined on PO Item
			code = getattr(src, "code_analytique", None)
			if code:
				it.code_analytique = code

			# Copy a more user-friendly description if available, without breaking standard naming
			desc = getattr(src, "item_name", None)
			# Prefer explicit custom description field when present
			if hasattr(src, "description") and getattr(src, "description"):
				desc = getattr(src, "description")

			# If PR item looks like a placeholder, improve the label; otherwise leave it intact
			if desc:
				current_name = getattr(it, "item_name", "") or ""
				placeholder_markers = {"BUDGET-LINE", code or ""}
				if current_name.strip() in placeholder_markers:
					it.item_name = desc


	@frappe.whitelist()
	def make_purchase_receipt_override(source_name, target_doc=None, args=None):
		"""Clean override of ERPNext PO->PR mapping used by the 'Get Items' button.

		Strategy:
		- Delegate to the core ERPNext mapping function to produce the PR document.
		- Post-process only the mapped child items to inject our custom fields:
		  * copy code_analytique
		  * set item_name from description when current item_name is a placeholder
		- Do not alter quantities, warehouses, rate, taxes, or dates.
		"""
		# 1) Call core implementation to build base PR
		core = frappe.get_attr("erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt")
		pr = core(source_name, target_doc=target_doc, args=args)

		# 2) Build a fast index of source PO Items by name
		if not pr or not getattr(pr, "items", None):
			return pr

		try:
			po = frappe.get_doc("Purchase Order", source_name)
		except Exception:
			return pr

		src_by_name = {getattr(it, "name", None): it for it in (po.get("items") or []) if getattr(it, "name", None)}

		# 3) Apply minimal enrichment to PR items
		for it in pr.items:
			po_item_name = getattr(it, "purchase_order_item", None) or getattr(it, "po_detail", None)
			if not po_item_name:
				continue
			src = src_by_name.get(po_item_name)
			if not src:
				continue

			code = getattr(src, "code_analytique", None)
			if code:
				it.code_analytique = code

			# Prefer custom description if present, else fall back to item_name on PO line
			desc = getattr(src, "description", None) or getattr(src, "item_name", None)
			if desc:
				current_name = getattr(it, "item_name", "") or ""
				placeholders = {"BUDGET-LINE", (code or "")}
				if current_name.strip() in placeholders:
					it.item_name = desc

		return pr


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

	Creates BUDGET-LINE item with proper expense account setup.
	
	Returns:
		dict: {'item_code': str, 'stock_uom': str}
	"""
	placeholder_code = 'BUDGET-LINE'
	
	# Get or create the item
	if frappe.db.exists('Item', placeholder_code):
		stock_uom = frappe.db.get_value('Item', placeholder_code, 'stock_uom')
		return {'item_code': placeholder_code, 'stock_uom': stock_uom or 'Nos'}
	
	# Create new budget placeholder item
	chosen_uom = _get_default_uom()
	item_group = _get_default_item_group()
	
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
	
	# Add expense account for each company
	_add_expense_accounts(doc)
	
	doc.insert(ignore_permissions=True)
	return {'item_code': placeholder_code, 'stock_uom': chosen_uom}


def _get_default_uom():
	"""Get a suitable UOM for the budget placeholder item."""
	preferred = ['Nos', 'Unit', 'Unité', 'PCE', 'Each']
	for uom in preferred:
		if frappe.db.exists('UOM', uom):
			return uom
	
	# Fallback to any UOM
	return frappe.db.get_value('UOM', {}, 'name') or 'Nos'


def _get_default_item_group():
	"""Get a suitable Item Group for the budget placeholder item."""
	if frappe.db.exists('Item Group', 'All Item Groups'):
		return 'All Item Groups'
	
	return frappe.db.get_value('Item Group', {}, 'name') or 'All Item Groups'


def _add_expense_accounts(item_doc):
	"""Add expense accounts for all companies to the item."""
	companies = frappe.get_all('Company', fields=['name', 'abbr'])
	
	for company in companies:
		expense_account = _get_expense_account(company.name, company.abbr)
		if expense_account:
			item_doc.append('item_defaults', {
				'company': company.name,
				'expense_account': expense_account
			})


def _get_expense_account(company_name, company_abbr):
	"""Get the best expense account for a company."""
	# Try common expense account patterns
	candidates = [
		f"Expenses - {company_abbr}",
		f"Direct Expenses - {company_abbr}",
		f"Cost of Goods Sold - {company_abbr}",
		f"Operating Expenses - {company_abbr}"
	]
	
	for candidate in candidates:
		if frappe.db.exists('Account', candidate):
			return candidate
	
	# Fallback: find any expense account for this company
	return frappe.db.get_value('Account', {
		'company': company_name,
		'account_type': 'Expense Account',
		'is_group': 0
	}, 'name')


def validate_purchase_order_item(doc, method):
	"""Custom validation for Purchase Order Item to ensure budget lines have proper items."""
	for item in doc.items:
		# If item has code_analytique but no valid item_code, set budget placeholder
		if item.code_analytique and (not item.item_code or item.item_code in [None, '', 'None']):
			placeholder_info = get_budget_placeholder_item()
			item.item_code = placeholder_info['item_code']
			
			# Ensure UOM consistency
			if not item.uom:
				item.uom = placeholder_info['stock_uom']
			if not item.stock_uom:
				item.stock_uom = placeholder_info['stock_uom']


def set_expense_account_for_budget_items(doc, method=None):
	"""Auto-set expense account for BUDGET-LINE items in Purchase Invoice."""
	if doc.doctype != "Purchase Invoice":
		return
	
	company = doc.company
	if not company:
		return
	
	company_abbr = frappe.get_cached_value('Company', company, 'abbr')
	expense_account = _get_expense_account(company, company_abbr)
	
	if not expense_account:
		return
	
	for item in doc.items:
		if item.item_code == 'BUDGET-LINE' and not item.expense_account:
			item.expense_account = expense_account


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_default_supplier_query(doctype, txt, searchfield, start, page_len, filters):
	"""Clean override of ERPNext Material Request supplier link query.
	
	Fixes SQL syntax error when Material Request has no items.
	
	Args:
		doctype: Target doctype (Supplier)
		txt: Search text
		searchfield: Field to search in
		start: Pagination start
		page_len: Results per page
		filters: Contains {"doc": "Material Request Name"}
	
	Returns:
		List of supplier records or empty list if no items
	"""
	# Extract Material Request name from filters
	mr_name = None
	if isinstance(filters, dict):
		mr_name = filters.get("doc")
	elif isinstance(filters, str):
		try:
			data = frappe.parse_json(filters)
			mr_name = data.get("doc") if isinstance(data, dict) else None
		except (ValueError, TypeError):
			pass
	
	if not mr_name:
		return []
	
	# Get Material Request document safely
	try:
		doc = frappe.get_doc("Material Request", mr_name)
	except frappe.DoesNotExistError:
		return []
	
	# Check if MR has items - return empty if not
	items = getattr(doc, "items", None)
	if not items or len(items) == 0:
		return []
	
	# Delegate to core ERPNext implementation
	try:
		core_func = frappe.get_attr(
			"erpnext.stock.doctype.material_request.material_request.get_default_supplier_query"
		)
		return core_func(doctype, txt, searchfield, start, page_len, filters)
	except Exception as e:
		frappe.log_error(f"Error calling core supplier query: {str(e)}", "Supplier Query Error")
		return []



