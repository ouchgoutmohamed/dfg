#!/usr/bin/env python3
"""
Test rapide pour valider la création d'Items à partir des budgets.

Usage: bench --site sdrt.localhost console
>>> exec(open('apps/sdrt/scripts/test_budget_item_creation.py').read())
"""

import frappe

def test_budget_item_creation():
	"""Test simple de création budget → item."""
	print("🧪 Test de création Budget → Item")
	
	# Nettoyer les données de test précédentes
	test_code = "TEST.DEMO.2025.CONV.UO.ACT.12345.NS.NS.NS"
	if frappe.db.exists("SDR Budget", test_code):
		frappe.delete_doc("SDR Budget", test_code, force=1)
	if frappe.db.exists("Item", test_code):
		frappe.delete_doc("Item", test_code, force=1)
	
	print("1️⃣ Création d'un budget de test...")
	
	try:
		# Créer les prérequis minimaux
		ensure_prerequisites()
		
		budget = frappe.get_doc({
			"doctype": "SDR Budget",
			"code_direction": "TEST",
			"code_programme": "DEMO", 
			"code_projet": "2025",
			"code_convention": "CONV",
			"code_uo": "UO",
			"code_action": "ACT",
			"compte_comptable": "12345",
			"description": "Test Peinture Salle Réunion",
			"montant": 1500
		})
		budget.insert(ignore_permissions=True)
		
		print(f"✅ Budget créé: {budget.name}")
		print(f"   Code analytique: {budget.code_analytique}")
		print(f"   Description: {budget.description}")
		
		# Vérifier que l'Item a été créé
		if frappe.db.exists("Item", budget.code_analytique):
			item = frappe.get_doc("Item", budget.code_analytique)
			print(f"✅ Item créé automatiquement:")
			print(f"   Item Code: {item.item_code}")
			print(f"   Item Name: {item.item_name}")
			print(f"   Stock UOM: {item.stock_uom}")
			print(f"   Item Group: {item.item_group}")
			print(f"   Is Stock Item: {item.is_stock_item}")
			print(f"   Is Purchase Item: {item.is_purchase_item}")
		else:
			print("❌ Item non créé - vérifier les logs d'erreur")
			
	except Exception as e:
		print(f"❌ Erreur lors du test: {str(e)}")
		import traceback
		traceback.print_exc()
		
	finally:
		# Nettoyer
		frappe.db.rollback()
		print("🧹 Données de test nettoyées")

def ensure_prerequisites():
	"""S'assurer que les prérequis existent."""
	# UOM
	if not frappe.db.exists("UOM", "Unité"):
		uom = frappe.get_doc({
			"doctype": "UOM", 
			"uom_name": "Unité",
			"enabled": 1
		})
		uom.insert(ignore_permissions=True)
		print("✅ UOM 'Unité' créée")
	
	# Item Group
	if not frappe.db.exists("Item Group", "All Item Groups"):
		root_group = frappe.get_doc({
			"doctype": "Item Group",
			"item_group_name": "All Item Groups",
			"is_group": 1
		})
		root_group.insert(ignore_permissions=True)
		print("✅ Item Group racine créé")
	
	if not frappe.db.exists("Item Group", "Tous les Groupes d'Articles"):
		group = frappe.get_doc({
			"doctype": "Item Group",
			"item_group_name": "Tous les Groupes d'Articles",
			"parent_item_group": "All Item Groups"
		})
		group.insert(ignore_permissions=True)
		print("✅ Item Group 'Tous les Groupes d'Articles' créé")

def test_import_scenario():
	"""Tester un scénario d'import avec données manquantes."""
	print("\n🧪 Test de scénario d'import avec données partielles")
	
	ensure_prerequisites()
	
	# Simuler une ligne d'import avec description vide
	budget = frappe.get_doc({
		"doctype": "SDR Budget",
		"code_direction": "IMP",
		"code_programme": "BATCH",
		"code_projet": "2025",
		"code_convention": "AUTO",
		"code_uo": "UO1",
		"code_action": "A01",
		"compte_comptable": "9999",
		"description": "",  # Description vide (cas d'import)
		"montant": 2500
	})
	
	try:
		budget.insert(ignore_permissions=True)
		
		if frappe.db.exists("Item", budget.code_analytique):
			item = frappe.get_doc("Item", budget.code_analytique)
			print(f"✅ Item créé même avec description vide:")
			print(f"   Item Name: {item.item_name} (doit être le code analytique)")
			print(f"   Item Code: {item.item_code}")
		else:
			print("❌ Item non créé pour ligne sans description")
			
	except Exception as e:
		print(f"❌ Erreur import: {e}")
	finally:
		frappe.db.rollback()

if __name__ == "__main__":
	print("🚀 Tests de validation Budget → Item")
	test_budget_item_creation()
	test_import_scenario()
	print("\n✅ Tests terminés")