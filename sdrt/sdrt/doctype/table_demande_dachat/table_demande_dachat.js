// Auto-calc "estimation" (qte * pu) live while editing rows of child table
// Minimal, clean implementation – similar behavior to Purchase Order Item.
// Server-side safety net already exists in the DocType Python class.

(function() {
	const doctype = 'table demande dachat';

	function compute(cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row) return;
		const q = frappe.utils.flt(row.qte) || 0;
		const pu = frappe.utils.flt(row.pu) || 0;
		const est = q * pu;

		// Avoid unnecessary model writes
		if (est >= 0 && row.estimation !== est) {
			frappe.model.set_value(cdt, cdn, 'estimation', est);
		}
	}

	frappe.ui.form.on(doctype, {
		qte: function(frm, cdt, cdn) { compute(cdt, cdn); },
		pu: function(frm, cdt, cdn) { compute(cdt, cdn); },
		// When row form is rendered (opening inline form), ensure value synced
		form_render: function(frm, cdt, cdn) { compute(cdt, cdn); }
	});
})();

