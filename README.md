# AleaQuant Web — V0

Site statique autonome, sans clé API côté navigateur. Sources livrées dans `dist/`.
Aucun historique en direct, aucune production LLM simulée. Le petit modèle des paires
est calculé exhaustivement dans le navigateur ; le dictionnaire contient 33 définitions
importées en lecture seule de loto-keno-lab-generic (feature_definitions.py, 29/09/2026).

Aperçu privé sur cette machine uniquement : `python3 -m http.server 4174 --bind 127.0.0.1 --directory dist`, puis ouvrir `http://127.0.0.1:4174/`. Arrêter le serveur avec `Ctrl+C`. Le binding `127.0.0.1` empêche l'accès depuis les autres appareils du réseau.

## Chaîne éditoriale

Les LLM tournent dans le dépôt indépendant `../aleaquant-editorial-agents`.
Après relecture et approbation explicite d’un brouillon, sa commande `editorial export`
émet un JSON versionné. Importer ce document ici avec :

```sh
python3 scripts/import_article.py ../aleaquant-editorial-agents/runs/solid-001/article.json
```

L’import est manuel et idempotent par article_id : une nouvelle version approuvée
remplace la précédente. Le JSON conserve les preuves et le hash de la version approuvée.
La mise en ligne reste une action distincte via Sites. Les brouillons ne sont jamais
copiés automatiquement dans `dist`. Le navigateur rend la prose comme texte, pas comme HTML.

## Suite

Brancher les métriques calculées sur le dépôt de données, produire et approuver le
premier article réel, puis choisir domaine personnalisé et audience. Le site est privé
au démarrage. Aucun CMS, Research Lab, formulaire factice ou collecte périodique ici.
