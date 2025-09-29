"""
Script utilitaire pour la gestion des Items créés à partir des budgets SDR.

Usage depuis bench console:
bench --site [site] console

Dans la console:
>>> exec(open('apps/sdrt/scripts/budget_items_utility.py').read())
>>> create_missing_items()                 # crée les Items manquants et met à jour la direction pour ceux existants
>>> backfill_item_directions()             # uniquement mise à jour du champ Item.direction d'après SDR Budget
>>> validate_budget_items()                # vérifications diverses
"""

import frappe

def create_missing_items(limit=None):
	"""Créer les Items manquants pour tous les budgets existants et
	mettre à jour le champ Item.direction d'après le budget pour les Items déjà présents.

	Args:
		limit (int): Limiter le nombre de budgets traités (pour tests)
	"""
	print("🔍 Recherche des budgets sans Items correspondants...")
	
	# Récupérer tous les budgets actifs
	filters = {"docstatus": ["!=", 2]}  # Exclure les annulés
	if limit:
		budgets = frappe.get_all("SDR Budget", 
			fields=["name", "code_analytique", "description"], 
			filters=filters,
			limit=limit
		)
	else:
		budgets = frappe.get_all("SDR Budget", 
			fields=["name", "code_analytique", "description"], 
			filters=filters
		)
	
	if not budgets:
		print("✅ Aucun budget trouvé.")
		return 0
	
	print(f"📊 {len(budgets)} budgets trouvés.")
	
	created_count = 0
	skipped_count = 0
	error_count = 0
	updated_direction = 0
	
	for budget_data in budgets:
		code = budget_data.code_analytique
		if not code:
			skipped_count += 1
			continue
			
		# Vérifier si Item existe déjà
		if frappe.db.exists("Item", {"item_code": code}):
			# Backfill direction pour les Items existants
			try:
				item_dir = frappe.db.get_value("Item", code, "direction")
				# Récupérer la valeur direction côté budget: prioriser le lien Direction sinon code_direction
				bud = frappe.get_doc("SDR Budget", budget_data.name)
				dir_value = None
				# Si le lien Direction est saisi, son autoname == valeur à stocker
				if getattr(bud, "direction", None):
					dir_value = str(bud.direction).strip()
				if not dir_value:
					dir_value = (getattr(bud, "code_direction", "") or "").strip()
				if dir_value and item_dir != dir_value:
					frappe.db.set_value("Item", code, "direction", dir_value)
					updated_direction += 1
			except Exception as e:
				# Ne pas bloquer, on continue
				print(f"⚠️  Impossible de mettre à jour direction pour Item {code}: {e}")
			skipped_count += 1
			continue
		
		try:
			# Charger le document complet pour accéder à toutes les méthodes
			budget_doc = frappe.get_doc("SDR Budget", budget_data.name)
			budget_doc._create_item_safely(
				code,
				budget_data.description or code,
				"Unité",
				"Tous les Groupes d'Articles"
			)
			created_count += 1
			
			if created_count % 50 == 0:
				print(f"⚡ {created_count} Items créés...")
				frappe.db.commit()  # Commit périodique
				
		except Exception as e:
			error_count += 1
			print(f"❌ Erreur pour budget {budget_data.name}: {str(e)}")
			continue
	
	frappe.db.commit()
	print(f"\n✅ Terminé!")
	print(f"   📦 Items créés: {created_count}")
	print(f"   🔄 Directions mises à jour (Items existants): {updated_direction}")
	print(f"   ⏭️  Ignorés (déjà existants sans changement): {skipped_count}")
	print(f"   ❌ Erreurs: {error_count}")
	
	return {"created": created_count, "direction_updated": updated_direction, "skipped": skipped_count, "errors": error_count}

def validate_budget_items():
	"""Valider la cohérence entre budgets et items."""
	print("🔍 Validation de la cohérence Budget ↔ Item...")
	
	budgets = frappe.get_all("SDR Budget", 
		fields=["name", "code_analytique", "description"],
		filters={"docstatus": ["!=", 2]}
	)
	
	issues = []
	
	for budget in budgets:
		code = budget.code_analytique
		if not code:
			issues.append(f"Budget {budget.name}: code_analytique manquant")
			continue
			
		item = frappe.db.get_value("Item", {"item_code": code}, 
			["name", "item_name", "description"], as_dict=True)
			
		if not item:
			issues.append(f"Budget {budget.name}: Item manquant (code: {code})")
		else:
			# Vérifier cohérence des descriptions
			if budget.description and item.item_name != budget.description:
				issues.append(
					f"Budget {budget.name}: descriptions incohérentes "
					f"(Budget: '{budget.description}' vs Item: '{item.item_name}')"
				)
	
	if issues:
		print(f"⚠️  {len(issues)} problèmes détectés:")
		for issue in issues[:10]:  # Limiter l'affichage
			print(f"   • {issue}")
		if len(issues) > 10:
			print(f"   ... et {len(issues) - 10} autres")
	else:
		print("✅ Aucun problème détecté!")
	
	return issues

def cleanup_orphaned_items(dry_run=True):
	"""Nettoyer les Items orphelins (sans budget correspondant).
	
	Args:
		dry_run (bool): Si True, affiche seulement ce qui serait supprimé
	"""
	print("🔍 Recherche des Items orphelins...")
	
	# Trouver tous les codes analytiques existants
	budget_codes = set(frappe.get_all("SDR Budget", 
		fields=["code_analytique"],
		filters={"docstatus": ["!=", 2]},
		pluck="code_analytique"
	))
	
	# Trouver tous les Items qui pourraient être des Items de budget
	# (heuristique: contiennent des points comme les codes analytiques)
	potential_budget_items = frappe.get_all("Item",
		fields=["item_code", "item_name"],
		filters={"item_code": ["like", "%.%"]}  # Contient au moins un point
	)
	
	orphans = []
	for item in potential_budget_items:
		if item.item_code not in budget_codes:
			orphans.append(item)
	
	if not orphans:
		print("✅ Aucun Item orphelin trouvé.")
		return []
	
	print(f"🗑️  {len(orphans)} Items orphelins trouvés:")
	for orphan in orphans[:5]:  # Afficher quelques exemples
		print(f"   • {orphan.item_code}: {orphan.item_name}")
	if len(orphans) > 5:
		print(f"   ... et {len(orphans) - 5} autres")
	
	if not dry_run:
		confirm = input(f"\n⚠️  Supprimer ces {len(orphans)} Items? (tapez 'OUI' pour confirmer): ")
		if confirm == "OUI":
			for orphan in orphans:
				try:
					frappe.delete_doc("Item", orphan.item_code)
					print(f"🗑️  Supprimé: {orphan.item_code}")
				except Exception as e:
					print(f"❌ Erreur lors de la suppression de {orphan.item_code}: {e}")
			frappe.db.commit()
			print(f"✅ {len(orphans)} Items orphelins supprimés.")
		else:
			print("❌ Suppression annulée.")
	else:
		print("\n💡 Exécutez cleanup_orphaned_items(dry_run=False) pour supprimer.")
	
	return orphans

def get_stats():
	"""Afficher les statistiques Budget/Item."""
	budget_count = frappe.db.count("SDR Budget", {"docstatus": ["!=", 2]})
	item_count = frappe.db.count("Item")
	budget_with_items = frappe.db.sql("""
		SELECT COUNT(DISTINCT b.name) 
		FROM `tabSDR Budget` b 
		INNER JOIN `tabItem` i ON b.code_analytique = i.item_code 
		WHERE b.docstatus != 2
	""")[0][0]
	
	print("📊 Statistiques Budget ↔ Item:")
	print(f"   📋 Budgets actifs: {budget_count}")
	print(f"   📦 Items total: {item_count}")
	print(f"   🔗 Budgets avec Item: {budget_with_items}")
	print(f"   ❓ Budgets sans Item: {budget_count - budget_with_items}")

def backfill_item_directions(limit=None, only_missing=True):
	"""Mettre à jour Item.direction pour les Items liés à des budgets (après import par ex.).

	Args:
		limit (int|None): Limiter le nombre de budgets traités.
		only_missing (bool): Si True, ne met à jour que lorsque le champ direction est vide.
	"""
	print("🔄 Backfill du champ direction sur les Items à partir des budgets…")
	filters = {"docstatus": ["!=", 2]}
	fields = ["name", "code_analytique", "direction", "code_direction"]

	budgets = frappe.get_all("SDR Budget", fields=fields, filters=filters, limit=limit)
	if not budgets:
		print("✅ Aucun budget trouvé.")
		return {"updated": 0, "skipped": 0}

	updated = 0
	skipped = 0
	errors = 0

	for b in budgets:
		code = (b.code_analytique or "").strip()
		if not code:
			skipped += 1
			continue
		if not frappe.db.exists("Item", code):
			skipped += 1
			continue

		desired = (b.direction or "").strip() or (b.code_direction or "").strip()
		try:
			current = frappe.db.get_value("Item", code, "direction") or ""
			if only_missing and current:
				skipped += 1
				continue
			if desired and current != desired:
				frappe.db.set_value("Item", code, "direction", desired)
				updated += 1
			else:
				skipped += 1
		except Exception as e:
			errors += 1
			print(f"⚠️  Erreur sur {code}: {e}")

	frappe.db.commit()
	print(f"✅ Backfill terminé. Mises à jour: {updated}, ignorés: {skipped}, erreurs: {errors}")
	return {"updated": updated, "skipped": skipped, "errors": errors}

# Fonctions de commodité
def quick_fix():
	"""Correction rapide : créer les Items manquants."""
	return create_missing_items()

def full_check():
	"""Vérification complète."""
	get_stats()
	print("\n" + "="*50)
	issues = validate_budget_items()
	print("\n" + "="*50)
	orphans = cleanup_orphaned_items(dry_run=True)
	return {"issues": issues, "orphans": orphans}

if __name__ == "__main__":
	print("🚀 Script utilitaire Budget → Item chargé!")
	print("Fonctions disponibles:")
	print("  • create_missing_items()")
	print("  • backfill_item_directions()")
	print("  • validate_budget_items()")
	print("  • cleanup_orphaned_items()")
	print("  • get_stats()")
	print("  • quick_fix()")
	print("  • full_check()")