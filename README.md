# AleaQuant Web — V0

Site statique autonome, sans clé API côté navigateur. Sources livrées dans `dist/`.
Aucun historique en direct, aucune production LLM simulée. Le petit modèle des paires
est calculé exhaustivement dans le navigateur ; le dictionnaire contient 33 définitions
importées en lecture seule de loto-keno-lab-generic (feature_definitions.py, 29/09/2026).

Aperçu privé sur cette machine uniquement : `python3 -m http.server 4174 --bind 127.0.0.1 --directory dist`, puis ouvrir `http://127.0.0.1:4174/`. Arrêter le serveur avec `Ctrl+C`. Le binding `127.0.0.1` empêche l'accès depuis les autres appareils du réseau.

## Déploiement

Le site est statique (`dist/`), sans étape de build : Cloudflare Workers (Static Assets)
sert le dossier tel quel.

**Dépôt** : `origin` est le dépôt GitHub privé `aleaquant`
(`https://github.com/christophecr-bit/aleaquant`).

**Hébergement retenu : Cloudflare Workers + Static Assets** (revu le 29/09/2026 — décision
initiale « Cloudflare Pages », changée après lecture de la doc officielle Cloudflare :
Workers + Static Assets est désormais le choix recommandé pour tout nouveau site, Pages
étant maintenu pour les projets existants). Raisons inchangées par rapport à Pages :
- Connexion à un dépôt GitHub *privé* sans condition de plan payant (contrairement à
  GitHub Pages qui exige Pro/Team/Enterprise pour un dépôt privé).
- Prise en charge native de `dist/_headers` (CSP, X-Content-Type-Options, etc.), à
  l'identique de Pages — seule différence : les en-têtes de `_headers` ne s'appliquent
  pas aux réponses générées par du code Worker (sans objet ici, site 100% statique).
- Migration vers Pages restée possible plus tard si besoin (guide officiel existe), mais
  aucune raison identifiée de partir sur Pages pour un projet neuf.

**Configuration effectuée le 29/09/2026** :
1. `wrangler.jsonc` à la racine du dépôt (`name: "aleaquant"`, `assets.directory: "./dist"`).
2. Authentification : `npx wrangler login` (OAuth, une fois, en local).
3. Premier déploiement manuel : `npx wrangler deploy` → sous-domaine public enregistré
   **https://aleaquant.aleaquant.workers.dev**.
4. Déploiement continu : Workers & Pages → `aleaquant` → Settings → Builds → Connect →
   dépôt GitHub `aleaquant`, branche de production `main`, aucune build command (site déjà
   statique). Chaque `git push` sur `main` redéploie automatiquement.

**En-têtes et robots** : `dist/_headers` (CSP simple, X-Content-Type-Options, X-Frame-
Options, Referrer-Policy) et `dist/robots.txt` (autorise l'indexation) sont lus
automatiquement au déploiement — rien à configurer côté tableau de bord.

**Domaine personnalisé** : pas encore configuré. Le sous-domaine `*.workers.dev` sert de
point d'entrée public en attendant (hors périmètre de ce chantier).

**Redéploiement manuel** (si besoin, hors CI) : `npx wrangler deploy` depuis la racine du
dépôt, avec une session `wrangler login` valide.

**Vérification** : un `git push` sur `main` doit se refléter sur l'URL publique en moins
de deux minutes.

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
# aleaquant
