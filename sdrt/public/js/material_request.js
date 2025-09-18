frappe.ui.form.on('Material Request', {
    refresh(frm) {
        // Ensure totals on load (in case draft opened and server already computed)
        recalc_total(frm);
    },
    // When the child table changes (row added/removed/reordered) recompute total
    demande_dachat_remove(frm) {
        recalc_total(frm);
    }
});

frappe.ui.form.on('table demande dachat', {
    qte(frm, cdt, cdn) { recalc_row_and_total(cdt, cdn, frm); },
    pu(frm, cdt, cdn) { recalc_row_and_total(cdt, cdn, frm); },
    demande_dachat_add(frm) { recalc_total(frm); },
});

function recalc_row_and_total(cdt, cdn, frm) {
    const row = frappe.get_doc(cdt, cdn);
    const qty = flt(row.qte) || 0;
    const pu = flt(row.pu) || 0;
    const new_estimation = qty * pu;
    if (row.estimation !== new_estimation) {
        frappe.model.set_value(cdt, cdn, 'estimation', new_estimation);
    }
    recalc_total(frm);
}

// function recalc_total(frm) {
//     let total = 0;
//     (frm.doc.demande_dachat || []).forEach(r => {
//         const val = flt(r.estimation) || 0;
//         total += val;
//     });
//     if (frm.doc.total_estimation !== total) {
//         frm.set_value('total_estimation', total);
//     }
// }
