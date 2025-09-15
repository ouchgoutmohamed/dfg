# Copyright (c) 2025, sdrt and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class MaterialRequest(Document):
	"""Customizations for Material Request without touching ERPNext core.

	- Aggregates estimation (qte * pu) from child table `demande_dachat` lines.
	- (Future) place for budget checks before submit.
	"""

	def validate(self):
		# Assure le recalcul des estimations lignes (plus fiable que d'attendre les hooks enfant)
		self._compute_line_estimations()
		self._compute_total_estimation()

	# ----------------------
	# Helpers
	# ----------------------
	def _compute_total_estimation(self):
		total = 0
		for row in self.get("demande_dachat") or []:
			if row.estimation:
				total += flt(row.estimation)
		# Store on a (to-be-created) custom field on Material Request: total_estimation
		if hasattr(self, "total_estimation"):
			self.total_estimation = total
		else:
			# Field not yet created – silent (avoids break). Optionally log later.
			pass

	def _compute_line_estimations(self):
		for row in self.get("demande_dachat") or []:
			qty = flt(row.qte) if row.qte else 0
			pu = flt(row.pu) if row.pu else 0
			row.estimation = qty * pu
			if row.estimation and row.estimation < 0:
				frappe.throw("L'estimation ne peut pas être négative (ligne: {0}).".format(row.idx))
