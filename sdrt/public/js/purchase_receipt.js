/*
Client-side guardrails for Purchase Receipt:
- Prevent default item_code = "1" from being used accidentally.
- When user selects a budget line (custom field code_analytique), ensure an Item exists with the same code.
- Keep standard ERPNext flows; do not override core methods.
*/

frappe.ui.form.on('Purchase Receipt', {
  setup(frm) {
    // nothing special
  },
});

frappe.ui.form.on('Purchase Receipt Item', {
  item_code: function(frm, cdt, cdn) {
    const d = locals[cdt][cdn];
    // If numeric-only item code sneaks in (like "1"), try to replace with code_analytique
    if (d.item_code && /^\d+$/.test(String(d.item_code))) {
      const fallback = d.code_analytique || '';
      if (fallback) {
        frappe.model.set_value(cdt, cdn, 'item_code', fallback);
      }
    }
  },

  code_analytique: function(frm, cdt, cdn) {
    const d = locals[cdt][cdn];
    if (!d.code_analytique) return;

    // Server creates or fetches the Item for this budget code
    frappe.call({
      method: 'sdrt.sdrt.custom.ensure_budget_item',
      args: {
        code: d.code_analytique,
        description: d.item_name || d.description || d.code_analytique
      },
      callback: (r) => {
        if (r.message) {
          const info = r.message;
          frappe.model.set_value(cdt, cdn, 'item_code', info.item_code);
          if (!d.item_name) {
            frappe.model.set_value(cdt, cdn, 'item_name', info.item_name || info.item_code);
          }
          if (!d.uom) {
            frappe.model.set_value(cdt, cdn, 'uom', info.stock_uom || 'Nos');
          }
          if (!d.stock_uom) {
            frappe.model.set_value(cdt, cdn, 'stock_uom', info.stock_uom || 'Nos');
          }
          if (!d.conversion_factor) {
            frappe.model.set_value(cdt, cdn, 'conversion_factor', 1);
          }
        }
      }
    });
  }
});
