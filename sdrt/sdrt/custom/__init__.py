"""Custom scripts and overrides for SDRT app.

Simple, clean implementation following KISS, DRY, YAGNI principles.
Only essential functionality to fix "Article 1 introuvable" error.
"""

import json
from typing import List, Dict, Optional
import frappe
from frappe import _
from frappe.utils import flt

__all__ = [
    'get_multi_da_budget_lines', 
    'make_purchase_receipt_override',
    'ensure_budget_placeholder_item',
    'setup_budget_system'
]


@frappe.whitelist()
def setup_budget_system():
    """Initialize the budget system with required items."""
    try:
        ensure_budget_placeholder_item()
        return {"status": "success", "message": "Budget system initialized"}
    except Exception as e:
        frappe.log_error(f"Error setting up budget system: {e}")
        return {"status": "error", "message": str(e)}


def ensure_budget_placeholder_item():
    """Create BUDGET-LINE item if it doesn't exist."""
    if frappe.db.exists('Item', 'BUDGET-LINE'):
        return
    
    # Get any valid UOM
    uom = 'Nos'
    if not frappe.db.exists('UOM', uom):
        uom = frappe.db.get_value('UOM', filters={}, fieldname='name') or 'Unit'
    
    # Get any valid Item Group
    item_group = frappe.db.get_value('Item Group', filters={}, fieldname='name') or 'All Item Groups'
    
    frappe.get_doc({
        'doctype': 'Item',
        'item_code': 'BUDGET-LINE',
        'item_name': 'Budget Line Item',
        'item_group': item_group,
        'stock_uom': uom,
        'is_stock_item': 0,
        'description': 'Placeholder for budget line items'
    }).insert(ignore_permissions=True)


@frappe.whitelist()
def make_purchase_receipt_override(source_name, target_doc=None, skip_item_mapping=False):
    """Simple override: fix invalid item codes before mapping.
    
    Follows KISS principle - minimal intervention, maximum compatibility.
    """
    # Ensure placeholder exists
    ensure_budget_placeholder_item()
    
    # Fix invalid items in source PO before mapping
    try:
        po_doc = frappe.get_doc("Purchase Order", source_name)
        _fix_invalid_items(po_doc)
        po_doc.save(ignore_permissions=True)  # Save fixes
    except Exception as e:
        frappe.log_error(f"Error fixing PO items: {e}")
    
    # Call standard ERPNext mapping
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt as standard_make_pr
    return standard_make_pr(source_name, target_doc, skip_item_mapping)


def _fix_invalid_items(doc):
    """Fix invalid item codes in document items table.
    
    Simple strategy: replace non-existent items with BUDGET-LINE.
    """
    for item in getattr(doc, 'items', []) or []:
        item_code = getattr(item, 'item_code', None)
        
        # Skip if item exists or is empty
        if not item_code or frappe.db.exists('Item', item_code):
            continue
        
        # Save original code for analytics if not already set
        if not getattr(item, 'code_analytique', None):
            item.code_analytique = item_code
        
        # Replace with valid placeholder
        item.item_code = 'BUDGET-LINE'
        item.item_name = 'Budget Line Item'
        
        # Ensure UOM is set
        if not getattr(item, 'stock_uom', None):
            item.stock_uom = _get_valid_uom()
        if not getattr(item, 'uom', None):
            item.uom = item.stock_uom


def _get_valid_uom():
    """Get a valid UOM from the system."""
    for uom in ['Nos', 'Unit', 'Each', 'PCE']:
        if frappe.db.exists('UOM', uom):
            return uom
    # Fallback to any UOM
    return frappe.db.get_value('UOM', filters={}, fieldname='name') or 'Nos'


# === BUDGET FUNCTIONS (simplified) ===

@frappe.whitelist()
def get_multi_da_budget_lines(material_requests: str, supplier: Optional[str] = None, purchase_order: Optional[str] = None):
    """Collect budget lines from multiple Material Requests."""
    if not material_requests:
        frappe.throw(_('Veuillez sélectionner au moins une Demande de Matériel.'))
    
    # Parse input
    if isinstance(material_requests, str):
        try:
            if material_requests.strip().startswith('['):
                mr_list = json.loads(material_requests)
            else:
                mr_list = [x.strip() for x in material_requests.split(',') if x.strip()]
        except (json.JSONDecodeError, ValueError):
            frappe.throw(_('Format de Demandes de Matériel invalide.'))
    else:
        mr_list = material_requests

    # Collect all lines
    all_rows = []
    for mr_name in mr_list:
        try:
            rows = _collect_da_lines(mr_name)
            all_rows.extend(rows)
        except Exception as e:
            frappe.log_error(f"Error collecting DA lines from {mr_name}: {e}")
    
    return all_rows


def _collect_da_lines(material_request: str) -> List[Dict]:
    """Collect budget lines from a Material Request."""
    mr = frappe.get_doc('Material Request', material_request)
    rows = []
    
    uom = _get_valid_uom()
    
    # Process custom budget lines table
    for line in getattr(mr, 'lignes_budgetaires', []) or []:
        row = {
            'item_code': '1',  # Placeholder - will be fixed by our override
            'item_name': getattr(line, 'libelle', '') or 'Budget Item',
            'description': getattr(line, 'libelle', ''),
            'qty': flt(getattr(line, 'quantite', 1)),
            'uom': uom,
            'stock_uom': uom,
            'rate': flt(getattr(line, 'prix_unitaire', 0)),
            'amount': flt(getattr(line, 'quantite', 1)) * flt(getattr(line, 'prix_unitaire', 0)),
            'material_request': material_request,
            'code_analytique': getattr(line, 'code_analytique', ''),
            'warehouse': mr.set_warehouse,
            'schedule_date': mr.schedule_date
        }
        rows.append(row)
    
    return rows
