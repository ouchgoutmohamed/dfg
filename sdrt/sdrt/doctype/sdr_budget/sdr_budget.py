# Copyright (c) 2025, sdrt and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


SEGMENT_FIELDS = [
	# Order of segments in the analytic code
	"code_direction",
	"code_programme",
	"code_projet",
	"code_convention",
	"code_uo",
	"code_action",
	"compte_comptable",
	"champ_libre_1",
	"champ_libre_2",
	"champ_libre_3",
]

PLACEHOLDER = "NS"  # Valeur par défaut si segment vide
SEPARATOR = "."     # Séparateur entre segments
MAX_LENGTH = 180      # Sécurité pour ne pas dépasser la longueur Data


class SDRBudget(Document):
	"""Controller du DocType SDR Budget.

	Construit le champ code_analytique (et donc le name via autoname field:code_analytique)
	en concaténant les codes composants. Ne modifie jamais le nom après insertion.
	"""

	def autoname(self):  # appelé uniquement lors de la création
		# S'assurer que le code_analytique est construit avant que Frappe n'utilise le champ
		if not self.code_analytique:
			self.code_analytique = self._build_code_analytique()

		if not self.code_analytique:
			# Fallback – ne devrait pas arriver car _build_code_analytique fournit toujours quelque chose
			frappe.throw("Impossible de générer le code analytique.")

		# Vérification unicité (le champ est unique mais on lève une erreur plus lisible)
		if frappe.db.exists("SDR Budget", self.code_analytique):
			frappe.throw(f"Un budget avec le code analytique {self.code_analytique} existe déjà.")

		# Nom = code_analytique (autoname: field:code_analytique)
		self.name = self.code_analytique

	def validate(self):
		# Si document déjà existant on ne régénère pas pour ne pas casser le name
		if self.is_new():
			return  # deja géré dans autoname

		# Option : si l'utilisateur a laissé code_analytique vide (cas de données importées) on le reconstruit
		if not self.code_analytique:
			new_code = self._build_code_analytique()
			# On ne peut pas changer self.name après insertion, donc on laisse seulement le champ informatif
			self.code_analytique = new_code

	def after_insert(self):
		"""Créer automatiquement un Item ERPNext pour chaque ligne budgétaire.

		- Item Code = code_analytique
		- Item Name = description
		- Description = description
		- Stock UOM = "Nos" (valeur standard ERPNext)
		- Item Group = "All Item Groups" (valeur standard ERPNext)

		KISS/DRY: idempotent, ne recrée pas si l'Item existe déjà.
		"""
		# Pré-conditions minimales
		code = (self.code_analytique or "").strip()
		if not code:
			# Rien à faire sans code analytique
			return

		# Ne rien faire si l'Item existe déjà
		if frappe.db.exists("Item", {"item_code": code}):
			return

		item_name = (self.description or code).strip()

		# Valeurs par défaut très sûres
		stock_uom = "Unité"
		item_group = "Tous les Groupes d'Articles"

		self._create_item_safely(code, item_name, stock_uom, item_group)

	def _create_item_safely(self, code, item_name, stock_uom, item_group):
		"""Créer un Item de manière sécurisée avec tous les contrôles nécessaires."""
		try:
			# Vérifications supplémentaires pour l'import
			if not self._validate_item_prerequisites(stock_uom, item_group):
				frappe.log_error(
					f"Prérequis manquants pour créer l'Item {code}",
					f"Stock UOM '{stock_uom}' ou Item Group '{item_group}' introuvable"
				)
				return

			# Validation longueur code ERPNext
			if len(code) > 140:  # Limite standard ERPNext
				frappe.log_error(
					f"Code analytique trop long pour Item: {code} ({len(code)} chars)",
					f"Budget {self.name}: code tronqué à 140 caractères"
				)
				code = code[:140]

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": code,
				"item_name": item_name[:140],  # Limite ERPNext
				"description": (self.description or item_name)[:1000] if self.description else item_name[:140],
				"stock_uom": stock_uom,
				"item_group": item_group,
				"is_stock_item": 0,
				"is_sales_item": 0,
				"is_purchase_item": 1,  # Ligne budgétaire = achat potentiel
				"include_item_in_manufacturing": 0,
			})
			item.insert(ignore_permissions=True)
			
		except frappe.DuplicateEntryError:
			# Item existe déjà, OK pour l'import
			pass
		except Exception:
			# Log détaillé pour debug import
			frappe.log_error(
				frappe.get_traceback(),
				f"Création Item échouée - Budget: {self.name}, Code: {code}, Description: {item_name}"
			)

	def _validate_item_prerequisites(self, stock_uom, item_group):
		"""Vérifier que les UOM et Item Group existent avant création Item."""
		# Vérifier UOM
		if not frappe.db.exists("UOM", stock_uom):
			# Créer UOM manquante
			try:
				frappe.get_doc({
					"doctype": "UOM", 
					"uom_name": stock_uom,
					"enabled": 1
				}).insert(ignore_permissions=True)
			except Exception:
				return False

		# Vérifier Item Group  
		if not frappe.db.exists("Item Group", item_group):
			# Item Group manquant, utiliser fallback
			return frappe.db.exists("Item Group", "All Item Groups")
			
		return True

	@staticmethod
	def create_items_for_existing_budgets():
		"""Méthode utilitaire pour créer les Items manquants pour budgets existants.
		
		Utiliser via bench console:
		from apps.sdrt.sdrt.sdrt.doctype.sdr_budget.sdr_budget import SDRBudget
		SDRBudget.create_items_for_existing_budgets()
		"""
		budgets = frappe.get_all("SDR Budget", 
			fields=["name", "code_analytique", "description"], 
			filters={"docstatus": ["!=", 2]}  # Pas les annulés
		)
		
		created_count = 0
		for budget_data in budgets:
			if not budget_data.code_analytique:
				continue
				
			if not frappe.db.exists("Item", {"item_code": budget_data.code_analytique}):
				try:
					budget_doc = frappe.get_doc("SDR Budget", budget_data.name)
					budget_doc._create_item_safely(
						budget_data.code_analytique,
						budget_data.description or budget_data.code_analytique,
						"Unité",
						"Tous les Groupes d'Articles"
					)
					created_count += 1
				except Exception:
					continue
					
		frappe.msgprint(f"Items créés: {created_count}/{len(budgets)}")
		return created_count

	# ----------------------
	# Helpers internes
	# ----------------------
	def _norm_segment(self, value):
		"""Nettoyage simple d'un segment.
		- strip
		- retire espaces internes
		- retourne PLACEHOLDER si vide
		"""
		if not value:
			return PLACEHOLDER
		# enlever espaces de début/fin
		value = value.strip()
		if not value:
			return PLACEHOLDER
		# supprimer espaces internes
		value = value.replace(" ", "")
		return value

	def _build_code_analytique(self):
		segments = []
		for field in SEGMENT_FIELDS:
			segments.append(self._norm_segment(self.get(field)))

		code = SEPARATOR.join(segments)

		if len(code) > MAX_LENGTH:
			frappe.throw(
				f"Code analytique trop long ({len(code)} > {MAX_LENGTH}). Réduisez la longueur de certains codes."
			)

		return code
