# Copyright (c) 2025, sdrt and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PurchaseOrderItem(Document):
	def validate(self):
		"""Ensure item_code is set for ERPNext compatibility."""
		if not self.item_code and self.code_analytique:
			# Use budget code as item_code for ERPNext compatibility
			self.item_code = self.code_analytique
		elif not self.item_code:
			# Default fallback
			self.item_code = "BUDGET-LINE"
			
		# Ensure item_name is set from budget description
		if self.code_analytique and not self.item_name:
			try:
				budget = frappe.get_doc("SDR Budget", self.code_analytique)
				if budget.description:
					self.item_name = budget.description
			except frappe.DoesNotExistError:
				pass
