import frappe
from frappe.utils import flt


def validate(doc, method=None):
    """Custom validation for Material Request.

    Ensures child table 'demande_dachat' lines have estimation = qte * pu
    (redundant safety) and optionally can aggregate if a target field exists later.
    """
    if not getattr(doc, 'demande_dachat', None):
        return

    for row in doc.demande_dachat:
        q = flt(row.qte) if row.qte else 0
        pu = flt(row.pu) if row.pu else 0
        expected = q * pu
        if row.estimation != expected:
            row.estimation = expected

    # If you later add a total field on parent, compute like:
    # doc.total_estimation = sum(flt(r.estimation) for r in doc.demande_dachat)
