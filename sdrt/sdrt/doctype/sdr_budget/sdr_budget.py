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
