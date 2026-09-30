# AleaQuant Web — V0

Site statique autonome, sans clé API côté navigateur. Sources livrées dans `dist/`.
Aucun historique en direct, aucune production LLM simulée. Le petit modèle des paires
est calculé exhaustivement dans le navigateur ; le dictionnaire contient 33 définitions
importées en lecture seule de loto-keno-lab-generic (feature_definitions.py, 29/09/2026).

## État des pages de tirage — 30 septembre 2026

`engine/build_pages.py` produit 1 985 pages EuroMillions et 7 672 pages Loto, plus un
sélecteur commun `/tirages/`, un index par jeu et un sitemap commun. Les faits Loto viennent du dépôt frère
`../aleaquant-data` et de `engine/facts_generic.py` ; les faits EuroMillions restent
issus du pilote publié, sans bascule de ses étoiles vers le moteur générique. L'outil
interactif de la page d'accueil est encore consacré à EuroMillions ; deux cartes
explicites donnent accès aux archives EuroMillions et Loto. Le plan de migration vers
un rendu par tirage à la demande, nécessaire avant Keno, est dans `docs/SCALING.md`.
Le calendrier de l'accueil reste EuroMillions ; l'archive Loto dispose de son propre
filtre par date, qui affiche les deux séances si elles ont eu lieu le même jour.
Chaque page de tirage est aussi l'adresse canonique de son récit : lorsqu'un article
est approuvé, l'import le relie par `research_pack.draw_id`, vérifie le SHA des faits
et actualise cette seule page. L'exemple publié est `EM-2011053`, tirage du
**6 septembre 2011**, à `/tirages/euromillions/2011-09-06/`. La plupart des pages
n'ont encore que leurs faits calculés ; leur récit attend le batch et la relecture
humaine. Aucun brouillon n'apparaît sur les pages publiques.

Les pages Loto utilisent `/tirages/loto/<draw_id>/` : 1 886 dates historiques ont un
premier et un second tirage, donc la date seule écraserait une page. Les pages nomment
la règle et la composante secondaire : la complémentaire ancienne était tirée mais ne
figurait pas sur la grille ; le numéro Chance actuel y figure. Les comparaisons
historiques des faits portent seulement sur le régime `k parmi n` comparable.

Pour régénérer les pages après mise à jour des faits :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python engine/build_pages.py
.venv/bin/python -m unittest discover -s tests
```

Ce build ne déploie rien sur Cloudflare. Le Journal et les pages sont à valider avant
`npx wrangler deploy`. Les détails de chaque fichier modifié et les dettes ouvertes sont
dans `docs/CHANGELOG.md` et `docs/TECHNICAL-DEBT.md`.

Le dépôt contient aussi les lois Keno 16/56 et 20/70 calculées par récurrence :
17 mesures sur 20 sont disponibles, et les trois absentes sont indiquées dans
`missing_fields`. Aucun fait ou page Keno n'est encore publié. Les JSON de faits
utilisés pour construire les pages restent versionnés, mais `dist/.assetsignore` les
exclut des assets envoyés à Cloudflare. Après génération : 19 346 fichiers dans
`dist/`, dont 9 658 faits intermédiaires. Wrangler a effectivement publié 9 686
assets lors du premier déploiement Loto le 30/09/2026 (9 688 après le calendrier) ;
deux pages Loto ont été vérifiées en HTTP 200 et une fiche
JSON exclue en HTTP 404.

Pour Keno, `engine/facts_generic.py` distingue désormais la probabilité d'un **tirage
exact** de toute probabilité de gain d'une grille jouée. Une génération ciblée par
`--draw` permet de qualifier quelques tirages sans écrire tout l'historique dans
`dist/`. Le prototype de groupes mensuels est dans `prototypes/keno-on-demand/` ;
il ne contient encore que les tirages bruts, pas les faits ni l'analyse publiable.

La maquette éditoriale locale est dans `prototypes/editorial-home/index.html`.
Elle distingue quatre rubriques (Tirages, Comprendre, Atlas & géométries,
Recherche & méthode) et utilise des cartes communes pour les contenus en ligne
et les sujets explicitement à préparer. Son fil des derniers tirages est encore
un snapshot. Le gabarit, les sources de données futures et les critères
d'intégration sont détaillés dans `docs/SITE-EDITORIAL-ARCHITECTURE.md`.
Les pages statiques de tirage régénérées **localement** affichent à nouveau des
mini-histogrammes issus des lois du régime concerné ; le trait orange situe la
valeur observée. Ce correctif n'est pas encore déployé sur le Worker.

Un **prototype local isolé** permet de tester un choix d'angle A/B/C et une relecture
de fluidité sur un rapport EuroMillions. Il sert à préparer la future chaîne
LangGraph dans le dépôt indépendant `../aleaquant-editorial-agents` ; il ne fait pas
partie du batch de constitution du fonds d'articles. Les titres citent leurs faits
d'appui et une sélection humaine est enregistrée avant l'essai direct :

```sh
.venv/bin/python agent/editorial_angle.py propose EM-26078
.venv/bin/python agent/editorial_angle.py show runs-angles/EM-26078/angles.json
.venv/bin/python agent/editorial_angle.py revise runs-angles/EM-26078/angles.json A --title "Une grille qui traverse quatre dizaines"
.venv/bin/python agent/editorial_angle.py choose runs-angles/EM-26078/angles.json A
.venv/bin/python agent/compose_draw_report.py EM-26078 --angle runs-angles/EM-26078/selected.json --write
.venv/bin/python agent/editorial_polish.py runs-llm-compose/EM-26078/draft.json
.venv/bin/python agent/draw_report.py show runs-llm-compose/EM-26078/draft-polished.json
```

La relecture humaine garde le dernier mot sur le titre et le corps. Les instructions
expérimentales sont dans `agent/prompts/`. Le batch `compose_batch_*` continue avec
son prompt et ses titres neutres ; il ne lit jamais `runs-angles/`. La conception
agentique cible, ses contrôles et ses étapes non opérationnelles sont suivis dans le
dépôt éditorial canonique.

Le dépôt `../aleaquant-editorial-agents` possède désormais un profil typé de
publication des tirages (`configs/draw-publication.json`) et un graphe court
pour contrôler les brouillons collectés puis attendre l'accord humain. Le
script `compose_batch_submit.py` accepte en option modèle, effort, fenêtre
et empreinte du profil ; sans ces options, son comportement historique demeure.
Le collecteur conserve le modèle réellement utilisé et l'empreinte éventuelle.
Ce raccordement ne soumet aucun batch et ne déploie aucun article à lui seul.

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
4. Aucun déploiement continu n'a été vérifié. La liaison GitHub → Cloudflare reste
   une tâche ouverte ; seul le déploiement Wrangler manuel est attesté.

**En-têtes et robots** : `dist/_headers` (CSP simple, X-Content-Type-Options, X-Frame-
Options, Referrer-Policy) et `dist/robots.txt` (autorise l'indexation) sont lus
automatiquement au déploiement — rien à configurer côté tableau de bord.

**Domaine personnalisé** : pas encore configuré. Le sous-domaine `*.workers.dev` sert de
point d'entrée public en attendant (hors périmètre de ce chantier).

**Redéploiement manuel** (si besoin, hors CI) : `npx wrangler deploy` depuis la racine du
dépôt, avec une session `wrangler login` valide.

**Un `git push` ne déploie RIEN** : il n'y a aucun CI, GitHub ne sert que d'archive. La
mise en ligne est toujours une action explicite, `npx wrangler deploy`, lancée depuis le
poste avec une session `wrangler login` valide. Les pages sont pré-générées dans `dist/`,
donc régénérer les faits sans relancer `engine/build_pages.py` laisse des pages obsolètes
en ligne.

**Vérification** : après un déploiement, l'URL publique doit refléter le contenu de
`dist/` en moins de deux minutes.

## Chaîne éditoriale

Deux chaînes distinctes, à ne pas confondre.

**1. Rapports de tirage — dans CE dépôt, `agent/`.** Un article par tirage, à partir des
faits calculés. Trois modes, dont un seul est retenu :

| Mode | Script | Statut |
|---|---|---|
| template déterministe | `agent/draw_report.py draft` | sans LLM, base de référence |
| reformulation | `agent/llm_rewrite_*.py`, `agent/llm_batch_*.py` | abandonné : le modèle ne voit que les claims déjà choisies, le résultat est cosmétique |
| **compose** | `agent/compose_draw_report.py` | **mode retenu** : le modèle reçoit les ~26 faits annotés et compose |

```sh
python3 agent/compose_draw_report.py EM-26077 --write
python3 agent/draw_report.py show runs-llm-compose/EM-26077/draft.json
python3 agent/draw_report.py approve runs-llm-compose/EM-26077/draft.json --reviewer "Christophe"
npx wrangler deploy
```

Le mode compose applique cinq gardes déterministes sur le texte produit : tout nombre doit
venir des faits ; un mot de rareté n'est autorisé que si la mesure **dépasse sa propre
référence** (`dist/data/rarity_profiles.json`, produit par `engine/rarity_profiles.py`) ;
aucun nom de code technique dans la prose ; chaque effectif de classe cité doit exister ;
aucun marqueur markdown. Quand un garde bloque, une passe de réparation renvoie au modèle
sa violation exacte, et n'est acceptée que si tous les gardes passent ensuite sans qu'un
nombre nouveau apparaisse. Une relecture de langue est appliquée puis rejetée si elle
touche un chiffre ou un mot de rareté. La note de méthode finale est une constante, pas
une phrase du modèle.

Point important : **une mesure dont la rareté est constante sur tout l'historique ne
porte aucune information.** Six des 26 mesures sont dans ce cas (les écarts ordonnés sont
« très rares » pour tout tirage possible), et 486 tirages sur 1984 n'ont aucune mesure
au-dessus de sa référence — pour eux, l'article ne doit employer aucun mot de rareté.

**2. Comité éditorial — dépôt indépendant `../aleaquant-editorial-agents`**
(pipeline LangGraph à 7 agents). Son POC traite actuellement des sujets structurés ;
la future chaîne pourra servir les articles de fond et des tirages sélectionnés, sans
se confondre avec le batch de fonds. Sa commande `editorial export` émet un JSON versionné,
importé ici avec :

```sh
python3 scripts/import_article.py ../aleaquant-editorial-agents/runs/solid-001/article.json
```

Dans les deux cas : l'import est manuel et idempotent par `article_id`, une nouvelle
version approuvée remplace la précédente, le JSON conserve les preuves et l'empreinte de
la version approuvée. Pour `draw_report`, l'identifiant doit être `tirage-<draw_id>` ;
l'import vérifie les faits du tirage et régénère sa page locale. Il ne déploie rien.
Les brouillons ne sont jamais copiés automatiquement dans `dist`.
Le Journal rend la prose avec `textContent` ; la page statique du tirage échappe
chaque paragraphe avant de l'insérer dans son HTML. Il n'y a donc pas de Markdown
ni de HTML interprété dans le corps ; toute mise en forme riche doit passer par
un champ structuré calculé côté Python.

## Rafraîchissement des tirages (chantier B3)

```sh
bash tools/refresh_draws.sh --check      # dit seulement où on en est
bash tools/refresh_draws.sh              # ingère, recalcule faits, profils et pages
```

Chaîne : ingestion de l'archive officielle FDJ dans le SQLite du laboratoire (append-only,
idempotente) → `engine/build_data.py` → `engine/rarity_profiles.py` →
`engine/build_pages.py`. Sans nouveau tirage, le script ne touche à rien et sort en 0.

**Il ne publie rien** : ni commit, ni `wrangler deploy`, ni approbation d'article. La mise
en ligne reste une décision humaine explicite.

Automatisation via launchd (mercredi et samedi, EuroMillions tirant le mardi et le
vendredi) :

```sh
cp tools/com.aleaquant.refresh.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.aleaquant.refresh.plist
tail -f ~/Library/Logs/aleaquant-refresh.log
```

Deux dépendances à connaître : `engine/build_data.py` exige **numpy** (simulations
Monte-Carlo de la section Lab, générateur à graine fixe), et l'URL de l'archive FDJ est
dans `tools/refresh.conf` — elle change quand FDJ ouvre une nouvelle période d'archive, et
l'ingestion refuse toute URL hors du domaine officiel, volontairement.

## Suite

État au 30/09/2026 :

- ~~Brancher les métriques calculées sur le dépôt de données~~ — **fait** : 1 984 tirages
  de faits, manifeste traçant le SHA de la base et des définitions.
- ~~Produire et approuver le premier article réel~~ — **fait le 30/09/2026** :
  `tirage-EM-2011053`, mode compose, approuvé et publié.
- **Choisir domaine personnalisé et audience** — à faire. Le site est privé au démarrage.

Chantiers suivants, par priorité : porter le mode compose dans les scripts Batch API
(ils portent encore la reformulation) avant de traiter l'historique complet ; afficher les
puces de rareté dans l'article pour les seules mesures au-dessus de leur référence ;
apparier chaque affirmation de rareté à son `fact_id` plutôt qu'à l'ensemble des faits.
Détail et invariants dans `docs/HANDOFF.md`, journal de conception dans
`docs/agent-editorial-v2-notes.md`.

Aucun CMS, Research Lab, formulaire factice ou collecte périodique ici.

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
