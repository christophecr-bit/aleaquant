# Règles de travail du site AleaQuant

- Préserver les changements présents, les données et les exécutions archivées.
- Appliquer la règle documentaire dans `docs/SITE-DOCUMENTATION-RULES.md`.
  Toute notion nécessaire à la compréhension d'une page possède une définition
  accessible et un lien vers un glossaire ou une explication réelle.
- Déclarer les prérequis versionnés des notions et contenus. Avant publication,
  contrôler toute leur chaîne : une cible locale ou un brouillon ne compte pas
  comme publié. Maintenir la progressivité, y compris pour un article expert.
- Raconter une question, une méthode, des résultats et leur portée en français
  lisible. Les identifiants, graines et paramètres internes appartiennent aux
  détails de reproductibilité, dépliables séparément.
- Versionner les éléments modifiés et mettre à jour le changelog et le registre
  concerné : backlog pour une fonction, TODO pour une action opérationnelle,
  dette technique pour une qualification ou un contrôle encore manquant.
- Suivre le plan `docs/DOCUMENTATION-PORTFOLIOS.md` ; vérifier les liens et les
  exemples. Distinguer intégration locale, recette et publication distante.
- Incrémenter directement le glossaire. Toute création ou révision d'article,
  mini-article ou parcours éditorial passe par le pipeline du dépôt canonique
  `../aleaquant-editorial-agents` et ses contrôles de preuves, relecture et
  approbation humaine du SHA. Ne pas publier un article par le générateur du
  glossaire. En attendant, les liens du site pointent vers les définitions réelles.
- Les constructions de recherche ont des graines et limites explicites, des
  références RANDOM comparables et une provenance ; aucun claim prédictif ni
  sélection de graines par performance Monte-Carlo.
