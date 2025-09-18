import frappe
from frappe.model.document import Document


class PurchaseOrderItem(Document):
	"""Minimal controller to avoid ImportError and follow Frappe conventions.

	Keep logic in parent Purchase Order hooks/custom code to minimize overrides here.
	"""
	pass


def on_doctype_update():
	"""Maintain useful index parity with ERPNext to avoid regressions."""
	try:
		frappe.db.add_index("Purchase Order Item", ["item_code", "warehouse"]) 
	except Exception:
		# Index may already exist or DB permissions may restrict; ignore silently
		pass
