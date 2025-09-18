# Public API wrappers for custom endpoints
import frappe
from sdrt.custom.purchase_order import create_po_from_demande_dachat as _impl

@frappe.whitelist()
def create_po_from_demande_dachat(material_requests, supplier, submit: int = 0):
    return _impl(material_requests, supplier, submit)
