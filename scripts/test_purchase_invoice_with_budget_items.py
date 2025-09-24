#!/usr/bin/env python3
"""
Test de validation finale pour la création d'Items avec comptes de charge.

Usage: bench --site sdrt.localhost console
>>> exec(open('apps/sdrt/scripts/test_purchase_invoice_with_budget_items.py').read())
"""

import frappe

def test_item_creation_with_accounts():
    """Tester la création d'Item avec les comptes de charge configurés."""
    print("🧪 Test de création Item avec comptes de charge")
    
    # Nettoyer les données de test
    test_code = "TEST.INVOICE.2025.CONV.UO.ACT.001.NS.NS.NS"
    cleanup_test_data(test_code)
    
    try:
        ensure_prerequisites()
        
        print("1️⃣ Création d'un budget avec Item automatique...")
        budget = frappe.new_doc("SDR Budget")
        budget.update({
            "code_direction": "TEST",
            "code_programme": "INVOICE",
            "code_projet": "2025",
            "code_convention": "CONV",
            "code_uo": "UO",
            "code_action": "ACT",
            "compte_comptable": "001",
            "description": "Matériel bureau - Test facture",
            "montant": 3000
        })
        budget.save(ignore_permissions=True)
        
        print(f"✅ Budget créé: {budget.name}")
        
        # Vérifier que l'Item a été créé avec les comptes
        if frappe.db.exists("Item", budget.code_analytique):
            item = frappe.get_doc("Item", budget.code_analytique)
            print(f"✅ Item créé: {item.item_code}")
            
            # Vérifier les Item Defaults
            if item.item_defaults:
                defaults = item.item_defaults[0]
                print(f"   Company: {defaults.company}")
                print(f"   Expense Account: {defaults.expense_account}")
                print(f"   Income Account: {defaults.income_account}")
                print(f"   Cost Center: {defaults.buying_cost_center}")
                
                if defaults.expense_account:
                    print("✅ Compte de charge configuré - Facture d'achat devrait fonctionner!")
                    return True
                else:
                    print("❌ Compte de charge manquant")
                    return False
            else:
                print("⚠️  Aucun Item Default trouvé")
                return False
        else:
            print("❌ Item non créé")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        frappe.db.rollback()

def simulate_purchase_invoice():
    """Simuler la création d'une facture d'achat pour tester."""
    print("\n🧪 Simulation création facture d'achat")
    
    try:
        ensure_prerequisites()
        
        # Créer d'abord un budget et son Item
        budget = frappe.new_doc("SDR Budget")
        budget.update({
            "code_direction": "TEST",
            "code_programme": "FACTURE",
            "code_projet": "2025",
            "code_convention": "CONV",
            "code_uo": "UO",
            "code_action": "ACT",
            "compte_comptable": "002",
            "description": "Fournitures bureau - Test facture",
            "montant": 2500
        })
        budget.save(ignore_permissions=True)
        
        if not frappe.db.exists("Item", budget.code_analytique):
            print("❌ Item non créé pour le budget")
            return False
            
        # Créer un fournisseur de test
        supplier_name = "Fournisseur Test"
        if not frappe.db.exists("Supplier", supplier_name):
            supplier = frappe.new_doc("Supplier")
            supplier.supplier_name = supplier_name
            supplier.save(ignore_permissions=True)
        
        # Obtenir la compagnie par défaut
        from erpnext import get_default_company
        company = get_default_company()
        
        print(f"2️⃣ Création facture d'achat avec Item: {budget.code_analytique}")
        
        # Créer la facture d'achat
        purchase_invoice = frappe.new_doc("Purchase Invoice")
        purchase_invoice.update({
            "supplier": supplier_name,
            "company": company,
            "posting_date": frappe.utils.today(),
            "due_date": frappe.utils.today(),
        })
        
        # Ajouter l'item
        item_row = purchase_invoice.append("items")
        item_row.update({
            "item_code": budget.code_analytique,
            "qty": 1,
            "rate": 2500,
            "code_analytique": budget.name  # Référence vers le budget
        })
        
        # Tenter de sauvegarder - cela devrait fonctionner maintenant
        purchase_invoice.save(ignore_permissions=True)
        
        print(f"✅ Facture d'achat créée: {purchase_invoice.name}")
        print(f"   Item utilisé: {item_row.item_code}")
        print(f"   Expense Account: {item_row.expense_account}")
        print(f"   Code Analytique: {item_row.code_analytique}")
        
        return True
        
    except Exception as e:
        if "Expense account is mandatory" in str(e):
            print(f"❌ Erreur compte de charge toujours manquant: {e}")
        else:
            print(f"❌ Autre erreur: {str(e)}")
        return False
    finally:
        frappe.db.rollback()

def cleanup_test_data(code):
    """Nettoyer les données de test."""
    if frappe.db.exists("Purchase Invoice", {"items": [["item_code", "=", code]]}):
        for pi in frappe.get_all("Purchase Invoice", filters={"items": [["item_code", "=", code]]}):
            frappe.delete_doc("Purchase Invoice", pi.name, force=1, ignore_permissions=True)
    if frappe.db.exists("SDR Budget", code):
        frappe.delete_doc("SDR Budget", code, force=1, ignore_permissions=True)
    if frappe.db.exists("Item", code):
        frappe.delete_doc("Item", code, force=1, ignore_permissions=True)
    if frappe.db.exists("Supplier", "Fournisseur Test"):
        frappe.delete_doc("Supplier", "Fournisseur Test", force=1, ignore_permissions=True)

def ensure_prerequisites():
    """S'assurer que les prérequis de base existent."""
    # UOM
    if not frappe.db.exists("UOM", "Unité"):
        uom = frappe.new_doc("UOM")
        uom.uom_name = "Unité"
        uom.save(ignore_permissions=True)
    
    # Item Group
    if not frappe.db.exists("Item Group", "All Item Groups"):
        root_group = frappe.new_doc("Item Group")
        root_group.item_group_name = "All Item Groups"
        root_group.is_group = 1
        root_group.save(ignore_permissions=True)
    
    if not frappe.db.exists("Item Group", "Tous les Groupes d'Articles"):
        group = frappe.new_doc("Item Group")
        group.item_group_name = "Tous les Groupes d'Articles"
        group.parent_item_group = "All Item Groups"
        group.save(ignore_permissions=True)

def run_complete_test():
    """Exécuter le test complet."""
    print("🚀 Test complet Item → Facture d'achat")
    print("=" * 50)
    
    test1_result = test_item_creation_with_accounts()
    test2_result = simulate_purchase_invoice()
    
    print("\n" + "=" * 50)
    print("📊 Résumé des tests:")
    print(f"   ✅ Test création Item avec comptes: {'PASS' if test1_result else 'FAIL'}")
    print(f"   ✅ Test simulation facture achat: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print("\n🎉 TOUS LES TESTS PASSENT!")
        print("✅ Le système est prêt pour l'utilisation en production")
        print("✅ Les Items créés depuis les budgets ont les comptes de charge requis")
        print("✅ Les factures d'achat peuvent utiliser ces Items sans erreur")
    else:
        print("\n⚠️  CERTAINS TESTS ÉCHOUENT")
        print("🔧 Vérifier la configuration des comptes de charge par défaut de l'entreprise")

if __name__ == "__main__":
    print("🚀 Script de test facture d'achat chargé!")
    print("Fonctions disponibles:")
    print("  • test_item_creation_with_accounts()")
    print("  • simulate_purchase_invoice()")
    print("  • run_complete_test()")
    print("\nPour exécuter le test complet:")
    print(">>> run_complete_test()")