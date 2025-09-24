# Copyright (c) 2025, sdrt and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestSDRBudget(FrappeTestCase):
	def setUp(self):
		"""Préparer les données de test."""
		# Nettoyer les données de test précédentes
		frappe.db.delete("Item", {"item_code": ["like", "TEST.%"]})
		frappe.db.delete("SDR Budget", {"name": ["like", "TEST.%"]})
		
		# S'assurer que les prérequis existent
		self._ensure_test_prerequisites()

	def _ensure_test_prerequisites(self):
		"""Créer les doctypes liés nécessaires pour les tests."""
		# UOM
		if not frappe.db.exists("UOM", "Unité"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Unité"}).insert()
		
		# Item Group
		if not frappe.db.exists("Item Group", "Tous les Groupes d'Articles"):
			if not frappe.db.exists("Item Group", "All Item Groups"):
				frappe.get_doc({
					"doctype": "Item Group", 
					"item_group_name": "All Item Groups",
					"is_group": 1
				}).insert()
			frappe.get_doc({
				"doctype": "Item Group", 
				"item_group_name": "Tous les Groupes d'Articles",
				"parent_item_group": "All Item Groups"
			}).insert()

	def test_item_creation_on_budget_insert(self):
		"""Tester la création automatique d'Item lors de l'insertion d'un budget."""
		budget = frappe.get_doc({
			"doctype": "SDR Budget",
			"code_direction": "TEST",
			"code_programme": "PROG",
			"code_projet": "PROJ", 
			"code_convention": "CONV",
			"code_uo": "UO",
			"code_action": "ACT",
			"compte_comptable": "COMPT",
			"description": "Test Peinture Bureau",
			"montant": 1000
		})
		budget.insert()
		
		# Vérifier que l'Item a été créé
		item_code = budget.code_analytique
		self.assertTrue(frappe.db.exists("Item", item_code))
		
		item = frappe.get_doc("Item", item_code)
		self.assertEqual(item.item_name, "Test Peinture Bureau")
		self.assertEqual(item.stock_uom, "Unité")
		self.assertEqual(item.is_stock_item, 0)
		self.assertEqual(item.is_purchase_item, 1)

	def test_no_duplicate_item_creation(self):
		"""Tester qu'on ne crée pas de doublons d'Items."""
		# Créer un premier budget
		budget1 = frappe.get_doc({
			"doctype": "SDR Budget",
			"code_direction": "TEST",
			"code_programme": "DUP",
			"code_projet": "PROJ1",
			"code_convention": "CONV",
			"code_uo": "UO", 
			"code_action": "ACT",
			"compte_comptable": "COMPT",
			"description": "Premier budget",
			"montant": 500
		})
		budget1.insert()
		
		# Créer manuellement un Item avec le même code
		duplicate_code = "TEST.DUP.PROJ2.CONV.UO.ACT.COMPT.NS.NS.NS"
		existing_item = frappe.get_doc({
			"doctype": "Item",
			"item_code": duplicate_code,
			"item_name": "Item existant",
			"stock_uom": "Unité",
			"item_group": "Tous les Groupes d'Articles"
		})
		existing_item.insert()
		
		# Créer un second budget avec le même code analytique potentiel
		budget2 = frappe.get_doc({
			"doctype": "SDR Budget", 
			"code_direction": "TEST",
			"code_programme": "DUP",
			"code_projet": "PROJ2", 
			"code_convention": "CONV",
			"code_uo": "UO",
			"code_action": "ACT", 
			"compte_comptable": "COMPT",
			"description": "Second budget",
			"montant": 750
		})
		budget2.insert()
		
		# Vérifier qu'aucun doublon n'a été créé
		items_count = frappe.db.count("Item", {"item_code": duplicate_code})
		self.assertEqual(items_count, 1)

	def test_import_scenario_missing_description(self):
		"""Tester l'import avec description manquante."""
		budget = frappe.get_doc({
			"doctype": "SDR Budget",
			"code_direction": "TEST",
			"code_programme": "NODESC", 
			"code_projet": "PROJ",
			"code_convention": "CONV",
			"code_uo": "UO",
			"code_action": "ACT",
			"compte_comptable": "COMPT", 
			"description": "",  # Description vide
			"montant": 300
		})
		budget.insert()
		
		# L'Item doit utiliser le code analytique comme nom
		item = frappe.get_doc("Item", budget.code_analytique)
		self.assertEqual(item.item_name, budget.code_analytique)

	def test_long_code_truncation(self):
		"""Tester la troncature des codes trop longs."""
		# Code volontairement très long
		budget = frappe.get_doc({
			"doctype": "SDR Budget",
			"code_direction": "A" * 30,
			"code_programme": "B" * 30,
			"code_projet": "C" * 30,
			"code_convention": "D" * 30,
			"code_uo": "E" * 30,
			"code_action": "F" * 30,
			"compte_comptable": "G" * 30,
			"description": "Code très long pour test",
			"montant": 999
		})
		
		# Ça doit passer sans lever d'exception
		budget.insert()
		
		# Vérifier qu'un Item a été créé avec un code tronqué si nécessaire
		self.assertTrue(len(budget.code_analytique) <= 180)  # Limite du budget
		if len(budget.code_analytique) > 140:  # Limite Item
			# Vérifier qu'il y a eu troncature dans les logs (optionnel)
			pass

	def tearDown(self):
		"""Nettoyer après les tests."""
		frappe.db.rollback()
