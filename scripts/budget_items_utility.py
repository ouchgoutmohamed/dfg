"""
Script utilitaire pour la gestion des Items créés à partir des budgets SDR.

Usage depuis bench console:
bench --site [site] console

Dans la console:
>>> exec(open('apps/sdrt/scripts/budget_items_utility.py').read())
>>> create_missing_items()
>>> # ou
>>> validate_budget_items()
"""

import frappe

def create_missing_items(limit=None):
	"""Créer les Items manquants pour tous les budgets existants.
	
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
	
	for budget_data in budgets:
		code = budget_data.code_analytique
		if not code:
			skipped_count += 1
			continue
			
		# Vérifier si Item existe déjà
		if frappe.db.exists("Item", {"item_code": code}):
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
	print(f"   ⏭️  Ignorés (déjà existants): {skipped_count}")
	print(f"   ❌ Erreurs: {error_count}")
	
	return created_count

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
	print("  • validate_budget_items()")
	print("  • cleanup_orphaned_items()")
	print("  • get_stats()")
	print("  • quick_fix()")
	print("  • full_check()")