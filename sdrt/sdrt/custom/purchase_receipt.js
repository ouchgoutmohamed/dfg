/**
 * Purchase Receipt customization for SDRT
 * Prevents pricing errors from invalid item codes
 */

frappe.ui.form.on('Purchase Receipt Item', {
    item_code: function(frm, cdt, cdn) {
        const item = locals[cdt][cdn];
        
        // If user manually enters a numeric item_code (like "1"), 
        // replace with placeholder to avoid pricing errors
        if (item.item_code && /^\d+$/.test(item.item_code.toString())) {
            frappe.model.set_value(cdt, cdn, 'item_code', 'BUDGET-LINE');
            frappe.show_alert({
                message: __('Invalid item code replaced with placeholder'),
                indicator: 'orange'
            });
        }
    },
    
    validate: function(frm, cdt, cdn) {
        const item = locals[cdt][cdn];
        
        // Ensure item_code is valid before processing
        if (item.item_code && !item.item_code.startsWith('BUDGET-LINE') && /^\d+$/.test(item.item_code.toString())) {
            frappe.model.set_value(cdt, cdn, 'item_code', 'BUDGET-LINE');
        }
    }
});

frappe.ui.form.on('Purchase Receipt', {
    refresh: function(frm) {
        // Add helpful note about item validation
        if (frm.doc.docstatus === 0 && frm.doc.items && frm.doc.items.length > 0) {
            const invalid_items = frm.doc.items.filter(item => 
                item.item_code && /^\d+$/.test(item.item_code.toString())
            );
            
            if (invalid_items.length > 0) {
                frm.dashboard.add_comment(__('Some item codes appear invalid and may cause errors. They will be automatically corrected on save.'), 'orange');
            }
        }
    }
});