/**
 * Minimal Purchase Order customization
 * Replaces "Get Items from Material Requests" with budget-based DA import
 * Preserves ERPNext standard workflows and statuses
 */

frappe.ui.form.on('Purchase Order', {
  refresh(frm) {
    // Only show custom button in draft mode
    if (frm.doc.docstatus === 0 && frm.doc.supplier) {
      frm.add_custom_button(__('Fetch Demande de Matériel'), 
        () => fetch_demande_materiel(frm), 
        __('Get Items From')
      );
    }

    // Normalize any duplicated description from previous imports
    if (frm.doc.docstatus === 0) {
      normalize_item_descriptions(frm);
    }
  },
  
  // Override the standard "Get Items from Material Requests" button
  get_items_from_open_material_requests(frm) {
    fetch_demande_materiel(frm);
  }
});

// Lightweight hooks to ensure calculations work with custom fields
frappe.ui.form.on('Purchase Order Item', {
  item_code: function(frm, cdt, cdn) {
    const it = locals[cdt][cdn];
    if (it.item_code && /^\d+$/.test(String(it.item_code))) {
      // If user typed a numeric code (like "1"), switch back to the budget item
      const fallback = it.code_analytique || '';
      if (fallback) {
        frappe.model.set_value(cdt, cdn, 'item_code', fallback);
      }
    }
  },
  code_analytique: function(frm, cdt, cdn) {
    const item = locals[cdt][cdn];
    // Ensure we use the real Item matching the budget code
    if (item.code_analytique) {
      frappe.model.set_value(cdt, cdn, 'item_code', item.code_analytique);
    }
    
    // Fetch description from budget and set as item name
    if (item.code_analytique) {
      frappe.call({
        method: 'frappe.client.get_value',
        args: {
          doctype: 'SDR Budget',
          filters: { name: item.code_analytique },
          fieldname: 'description'
        },
        callback: (r) => {
          if (r.message && r.message.description) {
            frappe.model.set_value(cdt, cdn, 'item_name', r.message.description);
          }
        }
      });
    }
    
    // Ensure schedule_date is valid
    validate_schedule_date(frm, cdt, cdn);
  },

  schedule_date: function(frm, cdt, cdn) {
    validate_schedule_date(frm, cdt, cdn);
  },

  qty: function(frm, cdt, cdn) {
    if (flt(locals[cdt][cdn].qty) && flt(locals[cdt][cdn].rate)) {
      frappe.model.set_value(cdt, cdn, 'amount', 
        flt(locals[cdt][cdn].qty) * flt(locals[cdt][cdn].rate));
    }
    frm.trigger('calculate_taxes_and_totals');
  },
  
  rate: function(frm, cdt, cdn) {
    if (flt(locals[cdt][cdn].qty) && flt(locals[cdt][cdn].rate)) {
      frappe.model.set_value(cdt, cdn, 'amount', 
        flt(locals[cdt][cdn].qty) * flt(locals[cdt][cdn].rate));
    }
    frm.trigger('calculate_taxes_and_totals');
  }
});

function validate_schedule_date(frm, cdt, cdn) {
  const item = locals[cdt][cdn];
  if (!item.schedule_date || !frm.doc.transaction_date) return;
  
  // Check if schedule_date is earlier than transaction_date
  if (frappe.datetime.get_diff(item.schedule_date, frm.doc.transaction_date) < 0) {
    // Set to 7 days from transaction_date
    const new_date = frappe.datetime.add_days(frm.doc.transaction_date, 7);
    frappe.model.set_value(cdt, cdn, 'schedule_date', new_date);
    frappe.show_alert({
      message: __('Required By date adjusted to be after transaction date'),
      indicator: 'orange'
    });
  }
}

function fetch_demande_materiel(frm) {
  if (!frm.doc.supplier) {
    frappe.msgprint(__('Please select a Supplier first.'));
    return;
  }

  // Use standard Material Request selector
  new frappe.ui.form.MultiSelectDialog({
    doctype: 'Material Request',
    target: frm,
    setters: {
      company: frm.doc.company || null
    },
    get_query() {
      return {
        filters: {
          docstatus: 1,
          material_request_type: 'Purchase'
        }
      };
    },
    action(selections) {
      if (selections.length > 0) {
        fetch_da_lines(frm, selections);
      }
    }
  });
}

function fetch_da_lines(frm, material_requests) {
  frappe.call({
    method: 'sdrt.sdrt.custom.get_multi_da_budget_lines',
    args: {
      material_requests: JSON.stringify(material_requests),
      supplier: frm.doc.supplier
    },
    freeze: true,
    freeze_message: __('Fetching budget lines...'),
    callback: (r) => {
      if (r.message && r.message.length > 0) {
        add_budget_lines_to_po(frm, r.message);
      } else {
        frappe.msgprint(__('No budget lines found.'));
      }
    }
  });
}

function add_budget_lines_to_po(frm, budget_lines) {
  // Add lines to Purchase Order using the auto-created Item matching the budget code
  const added_rows = [];
  budget_lines.forEach(line => {
    const item = frm.add_child('items');

    // Use the real Item code equal to the budget analytic code
    item.item_code = line.code_analytique || '';
    item.code_analytique = line.code_analytique;
    item.item_name = (line.description && line.description.trim()) ? line.description : (line.code_analytique || __('Budget Line'));
    item.details = '';

    // Quantities and rates
    item.qty = line.qty || 1;
    item.rate = line.rate || 0;
    item.uom = line.uom || 'Nos';
    item.stock_uom = line.uom || 'Nos';
    item.conversion_factor = 1;
    
    // Ensure schedule_date is not earlier than transaction_date
    let schedule_date = line.schedule_date || frm.doc.schedule_date;
    if (!schedule_date || frappe.datetime.get_diff(schedule_date, frm.doc.transaction_date) < 0) {
      schedule_date = frappe.datetime.add_days(frm.doc.transaction_date, 7);
    }
    item.schedule_date = schedule_date;

    // Pre-calc amount for grid display; ERPNext will recompute
    item.amount = (flt(item.qty) || 0) * (flt(item.rate) || 0);

    added_rows.push({ doctype: item.doctype, name: item.name });
  });

  // Refresh and trigger calculations
  frm.refresh_field('items');

  // Normalize labels vs details for clean UI
  normalize_item_descriptions(frm);

  // Trigger qty event for each added row to ensure totals recalc
  setTimeout(() => {
    (added_rows || []).forEach(r => {
      frm.script_manager.trigger('qty', r.doctype, r.name);
    });
    frm.trigger('calculate_taxes_and_totals');
    frm.refresh_fields();
  }, 100);

  frappe.show_alert({
    message: __('Added {0} budget lines', [budget_lines.length]),
    indicator: 'green'
  });
}function normalize_item_descriptions(frm) {
  let changed = false;
  (frm.doc.items || []).forEach(it => {
    const name_is_budget_code = it.item_name && it.code_analytique && it.item_name.trim() === it.code_analytique.trim();
    const has_details_desc = it.details && String(it.details).trim().length > 0;
    if (name_is_budget_code && has_details_desc) {
      // Move details to short description and clear details
      it.item_name = String(it.details).trim();
      it.details = '';
      changed = true;
    }
  });
  if (changed) {
    frm.refresh_field('items');
  }
}
