# AleaQuant Web — V0

Site statique autonome, sans clé API côté navigateur. Sources livrées dans `dist/`.
Aucun historique en direct, aucune production LLM simulée. Le petit modèle des paires
est calculé exhaustivement dans le navigateur ; le dictionnaire contient 33 définitions
importées en lecture seule de loto-keno-lab-generic (feature_definitions.py, 29/09/2026).

Aperçu : `python3 -m http.server 4173 --directory dist`.

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

## V0 tirages : moteur, facts, agent (branche `v0-draws`)

Chaîne complète, locale et reproductible :

```sh
# 1. Lois exactes (une seule fois, ~1 min ; à refaire seulement si patterns.py change)
python3 engine/exact_laws.py
# 2. Moteur statistique : historique SQLite du laboratoire -> dist/data/*.json + facts
python3 engine/build_data.py            # --facts 12 par défaut, --draw EM-26077 en plus
# 3. Agent de publication : facts -> brouillon traçable (rien n'est publié)
python3 agent/draw_report.py draft dist/data/facts/latest.json
# 4. Validation humaine -> import dans dist/articles.json (import_article.py inchangé)
python3 agent/draw_report.py approve runs/EM-26077/draft.json --reviewer "Christophe"
```

- Le moteur lit `../loto-keno-lab-generic` en lecture seule (variable `ALEAQUANT_LAB` pour un autre chemin) :
  base `data/history/euromillions.sqlite3`, définitions `patterns.py`, catalogues de portefeuilles.
- `dist/data/manifest.json` trace le SHA de la base, la version du moteur et le SHA des définitions.
- Les facts n'utilisent que les tirages antérieurs au tirage analysé (pas de look-ahead).
- L'agent n'a accès qu'au JSON de facts. Chaque phrase cite ses facts ; un garde bloque
  tout nombre absent des facts cités. Le brouillon n'entre dans le journal qu'après `approve`.
- Géométries de portefeuilles : génération 1 (recherche HPC, Monte-Carlo puis exact).
  Les générations suivantes s'ajoutent comme nouvelles entrées dans `atlas.json`.

Sections ajoutées au site : `#tirages`, `#atlas`, `#geometries`, `#lab` (fichiers `draws.js`, `atlas.css`).
Un tirage précis s'ouvre avec `#EM-26077`.
