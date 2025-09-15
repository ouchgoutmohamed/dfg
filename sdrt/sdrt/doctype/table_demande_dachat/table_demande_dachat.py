# Copyright (c) 2025, sdrt and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class tabledemandedachat(Document):
	"""Child table line for Demande d'achat.

	Automatically computes `estimation` = qte * pu on every validate
	(server-side, so no core change and always consistent even via import/API).
	"""

	def before_insert(self):
		# compute once at creation
		self._compute_estimation()

	def before_save(self):
		# recompute if qty or price changed
		self._compute_estimation()

	def before_validate(self):  # fallback (legacy) ensure value present
		if not self.estimation:
			self._compute_estimation()

	def _compute_estimation(self):
		qty = flt(self.qte) if self.qte else 0
		pu = flt(self.pu) if self.pu else 0
		# Currency field: let Frappe handle precision; still ensure numeric
		self.estimation = qty * pu

		# Optional: guard against accidental huge numbers (basic sanity)
		if self.estimation and self.estimation < 0:
			frappe.throw("L'estimation ne peut pas être négative.")

		# (If you later want a per-line max, add another check here.)
