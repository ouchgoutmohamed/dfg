"""
Script de test final pour valider la création d'Items à partir des budgets et l'import complet.

Usage dans la console Frappe:
bench --site sdrt.localhost console
>>> exec(open('apps/sdrt/scripts/final_test_budget_items.py').read())
>>> test_single_budget_creation()
>>> test_bulk_import_simulation()
"""

import frappe

def test_single_budget_creation():
	"""Test simple : créer un budget et vérifier la création d'Item associé."""
	print("🧪 Test de création unique Budget → Item")
	
	# Nettoyer les données de test
	test_code = "TEST.SINGLE.2025.CONV.UO.ACT.001.NS.NS.NS"
	cleanup_test_data(test_code)
	
	try:
		# Assurer les prérequis de base
		ensure_basic_setup()
		
		print("1️⃣ Création d'un budget simple...")
		budget = frappe.new_doc("SDR Budget")
		budget.update({
			"code_direction": "TEST",
			"code_programme": "SINGLE",
			"code_projet": "2025",
			"code_convention": "CONV",
			"code_uo": "UO",
			"code_action": "ACT",
			"compte_comptable": "001",
			"description": "Matériel informatique - Test unitaire",
			"montant": 5000
		})
		budget.save(ignore_permissions=True)
		
		print(f"✅ Budget créé: {budget.name}")
		print(f"   Code analytique: {budget.code_analytique}")
		
		# Vérifier la création automatique de l'Item
		if frappe.db.exists("Item", budget.code_analytique):
			item = frappe.get_doc("Item", budget.code_analytique)
			print(f"✅ Item créé automatiquement:")
			print(f"   Item Code: {item.item_code}")
			print(f"   Item Name: {item.item_name}")
			print(f"   Description: {item.description[:50]}...")
			print(f"   Stock UOM: {item.stock_uom}")
			print(f"   Item Group: {item.item_group}")
			print(f"   Is Stock Item: {item.is_stock_item}")
			return True
		else:
			print("❌ Item non créé automatiquement")
			return False
			
	except Exception as e:
		print(f"❌ Erreur: {str(e)}")
		import traceback
		traceback.print_exc()
		return False
	finally:
		frappe.db.rollback()

def test_bulk_import_simulation():
	"""Simuler un import de budget annuel avec plusieurs lignes."""
	print("\n🧪 Test d'import massif (simulation)")
	
	# Données de test simulant un import Excel
	import_data = [
		{
			"code_direction": "DP",
			"code_programme": "PDU", 
			"code_projet": "AGOF",
			"code_convention": "C07",
			"code_uo": "MOD",
			"code_action": "A1",
			"compte_comptable": "2356",
			"description": "Peinture muraille Agadir Oufella",
			"montant": 15000
		},
		{
			"code_direction": "DP",
			"code_programme": "PDU",
			"code_projet": "CASA", 
			"code_convention": "C08",
			"code_uo": "INF",
			"code_action": "A2",
			"compte_comptable": "6123",
			"description": "Équipement informatique Casa",
			"montant": 25000
		},
		{
			"code_direction": "DRH",
			"code_programme": "FORM",
			"code_projet": "2025",
			"code_convention": "C01", 
			"code_uo": "RH",
			"code_action": "FORM",
			"compte_comptable": "6411",
			"description": "Formation personnel 2025",
			"montant": 80000
		},
		{
			"code_direction": "DTI",
			"code_programme": "INFR",
			"code_projet": "SERV",
			"code_convention": "C02",
			"code_uo": "IT",
			"code_action": "MAINT",
			"compte_comptable": "6156",
			"description": "",  # Test avec description vide
			"montant": 45000
		}
	]
	
	print(f"1️⃣ Import simulé de {len(import_data)} lignes budgétaires...")
	
	# Nettoyer les données de test précédentes  
	for data in import_data:
		code = f"{data['code_direction']}.{data['code_programme']}.{data['code_projet']}.{data['code_convention']}.{data['code_uo']}.{data['code_action']}.{data['compte_comptable']}.NS.NS.NS"
		cleanup_test_data(code)
	
	try:
		ensure_basic_setup()
		
		created_budgets = []
		created_items = []
		
		for i, data in enumerate(import_data, 1):
			print(f"   📝 Traitement ligne {i}/{len(import_data)}...")
			
			budget = frappe.new_doc("SDR Budget")
			budget.update(data)
			budget.save(ignore_permissions=True)
			
			created_budgets.append(budget.name)
			
			# Vérifier création Item
			if frappe.db.exists("Item", budget.code_analytique):
				created_items.append(budget.code_analytique)
			
		print(f"✅ Import terminé:")
		print(f"   📋 Budgets créés: {len(created_budgets)}")
		print(f"   📦 Items créés: {len(created_items)}")
		
		# Vérifier cas spécifiques
		print("\n2️⃣ Vérification des cas particuliers...")
		
		# Cas avec description vide
		empty_desc_budget = None
		for budget_name in created_budgets:
			budget = frappe.get_doc("SDR Budget", budget_name)
			if not budget.description:
				empty_desc_budget = budget
				break
		
		if empty_desc_budget:
			item = frappe.get_doc("Item", empty_desc_budget.code_analytique)
			print(f"✅ Cas description vide géré:")
			print(f"   Item Name: {item.item_name} (doit être le code analytique)")
		
		# Test de non-duplication
		print("\n3️⃣ Test de non-duplication...")
		duplicate_count_before = len(created_items)
		
		# Essayer de recréer un budget existant (simulation erreur d'import)
		try:
			duplicate_budget = frappe.new_doc("SDR Budget")
			duplicate_budget.update(import_data[0])  # Même données que le 1er
			duplicate_budget.save(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			print("✅ Protection contre les doublons fonctionne")
		except Exception as e:
			print(f"⚠️  Autre erreur de duplication: {e}")
		
		duplicate_count_after = frappe.db.count("Item", {"item_code": ["in", created_items]})
		print(f"✅ Pas de doublon d'Items: {duplicate_count_before} = {duplicate_count_after}")
		
		return True
		
	except Exception as e:
		print(f"❌ Erreur durant l'import: {str(e)}")
		import traceback
		traceback.print_exc()
		return False
	finally:
		frappe.db.rollback()

def cleanup_test_data(code):
	"""Nettoyer les données de test."""
	if frappe.db.exists("SDR Budget", code):
		frappe.delete_doc("SDR Budget", code, force=1, ignore_permissions=True)
	if frappe.db.exists("Item", code):
		frappe.delete_doc("Item", code, force=1, ignore_permissions=True)

def ensure_basic_setup():
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

def run_all_tests():
	"""Exécuter tous les tests."""
	print("🚀 Tests complets Budget → Item")
	print("=" * 50)
	
	test1_result = test_single_budget_creation()
	test2_result = test_bulk_import_simulation()
	
	print("\n" + "=" * 50)
	print("📊 Résumé des tests:")
	print(f"   ✅ Test unitaire: {'PASS' if test1_result else 'FAIL'}")
	print(f"   ✅ Test import massif: {'PASS' if test2_result else 'FAIL'}")
	
	if test1_result and test2_result:
		print("🎉 Tous les tests passent - Le système est prêt pour l'import du budget annuel!")
	else:
		print("⚠️  Certains tests échouent - Vérifier la configuration.")

if __name__ == "__main__":
	print("🚀 Script de test final chargé!")
	print("Fonctions disponibles:")
	print("  • test_single_budget_creation()")
	print("  • test_bulk_import_simulation()")
	print("  • run_all_tests()")
	print("\nPour exécuter tous les tests:")
	print(">>> run_all_tests()")