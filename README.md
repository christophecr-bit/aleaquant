# AleaQuant Web — V0

Site statique autonome, sans clé API côté navigateur. Sources livrées dans `dist/`.
Aucun historique en direct, aucune production LLM simulée. Le petit modèle des paires
est calculé exhaustivement dans le navigateur ; le dictionnaire conserve 34 définitions
de grilles et comprend désormais 19 métriques de portefeuilles versionnées.
La provenance des définitions de grilles reste le dictionnaire de loto-keno-lab-generic.

Registres de pilotage : [backlog produit](docs/PRODUCT-BACKLOG.md),
[TODO opérationnelle](docs/OPERATIONAL-TODO.md), [cadrage](docs/TASKS.md),
[dette technique](docs/TECHNICAL-DEBT.md) et
[inventaire des composants](docs/COMPONENT-INVENTORY.md).
Les changements du modèle scientifique seront consignés dans le
[registre de versions canonique](../aleaquant-data/docs/MODEL-CHANGELOG.md).

Règle éditoriale du site : [progressivité et dépendances](docs/SITE-DOCUMENTATION-RULES.md).
Les notions ont des prérequis versionnés, publiés avant les pages et articles qui
en dépendent. Le [plan des portefeuilles](docs/DOCUMENTATION-PORTFOLIOS.md) distingue
le glossaire directement incrémenté et les articles soumis au pipeline éditorial.
Pour reconstruire uniquement le glossaire local : `python3 engine/build_glossary.py`.
Cette commande ne publie rien à distance. Les compétences d'agents adaptées aux
niveaux d'articles sont à reprendre sous PB-017 / TD-EDIT-001.

Les nouvelles [études avec RANDOM](docs/PORTFOLIO-CONTROLLED-STUDIES.md) se lancent
par `python engine/study.py run --study-config CONFIG --run-dir NOUVEAU_DOSSIER`.
Le guide décrit configuration, progression, arrêts et reprises. Les deux exemples
ont été exécutés et sont consultables dans `/portefeuilles/`, avec leurs archives.

## État des pages de tirage — 2 octobre 2026

`engine/build_pages.py` produit localement 1 985 pages EuroMillions, 7 673 pages Loto
et 333 fiches Keno du régime actif 16/56, plus un sélecteur commun `/tirages/`, un index
par jeu et un sitemap commun. Les faits Loto viennent du dépôt frère
`../aleaquant-data` et de `engine/facts_generic.py` ; les faits EuroMillions restent
issus du pilote publié, sans bascule de ses étoiles vers le moteur générique. L'outil
interactif de la page d'accueil est encore consacré à EuroMillions ; deux cartes
explicites donnent accès aux archives des trois jeux dans le build local. Le Worker
public n'a pas encore reçu les pages Keno ; le régime historique 20/70 attend toujours
un rendu à la demande. Le plan est dans `docs/SCALING.md`.
Le calendrier de l'accueil reste EuroMillions ; l'archive Loto dispose de son propre
filtre par date, qui affiche les deux séances si elles ont eu lieu le même jour.
Les pages de tirage dessinent toutes les lois **numériques** disponibles :
18 mini-histogrammes sur la fiche Loto du 28/09/2026. Chaque classe apparaît comme
sur la sparkline de l'accueil, sans regroupement graphique ; le trait orange situe la
valeur observée. Les signatures sans axe naturel (écarts ordonnés et répartition par
dizaines) restent textuelles, avec les bornes de chaque dizaine explicitées sur les
cartes des trois jeux. Loto 5/49 et EuroMillions 5/50 ont des lois distinctes ;
leurs silhouettes proches ne sont pas identiques. Une hauteur minimale d'un pixel
garde les queues visibles sans modifier la distribution.
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

Le régime Keno 16/56 contient 20 lois exactes locales, dont deux issues du scan Metal
complet. Le rattrapage du 01/10 a calculé les **19 465 fiches Keno** et peuplé les
profils des deux régimes : 333 tirages en 16/56 et 19 133 en 20/70. Pour 20/70,
17 lois sur 20 sont disponibles et trois champs restent explicitement absents. La
comparaison indépendante intégrale avec Rayon reste à faire. Les 333 pages 16/56 sont
en recette locale ; aucune n'a été déployée.
Les JSON de faits
utilisés pour construire les pages restent versionnés, mais `dist/.assetsignore` les
exclut des assets envoyés à Cloudflare. Avant le nouveau cycle local : 19 346 fichiers
dans `dist/`, dont 9 658 faits intermédiaires. Wrangler a effectivement publié 9 686
assets lors du premier déploiement Loto le 30/09/2026 (9 688 après le calendrier) ;
deux pages Loto ont été vérifiées en HTTP 200 et une fiche
JSON exclue en HTTP 404.

Pour Keno, `engine/facts_generic.py` distingue désormais la probabilité d'un **tirage
exact** de toute probabilité de gain d'une grille jouée. Une génération ciblée par
`--draw` permet de qualifier quelques tirages sans écrire tout l'historique dans
`dist/`. Le prototype de groupes mensuels est dans `prototypes/keno-on-demand/` ;
il ne contient encore que les tirages bruts, pas les faits ni l'analyse publiable.

La maquette éditoriale est dans `prototypes/editorial-home/index.html` et consultable
à distance sur [le Worker, sous /maquette/](https://aleaquant.aleaquant.workers.dev/maquette/).
Elle distingue quatre rubriques (Tirages, Comprendre, Atlas & géométries,
Recherche & méthode) et utilise des cartes communes pour les contenus en ligne
et les sujets explicitement à préparer. Son fil des derniers tirages est encore
un snapshot. Le gabarit, les sources de données futures et les critères
d'intégration sont détaillés dans `docs/SITE-EDITORIAL-ARCHITECTURE.md`.
Les fonctions attendues sont listées dans `docs/ROADMAP.md` ; les composants
techniques restant à réaliser sont suivis dans `docs/TECHNICAL-DEBT.md` ; les
explorations ponctuelles sont dans `docs/TASKS.md`.
Les pages statiques de tirage affichent des mini-histogrammes issus des lois du régime
concerné ; leur dessin reprend désormais la sparkline de l'accueil, classe par classe.
Cette dernière harmonisation est locale et reste à déployer ; le précédent correctif
et la maquette sont déjà en ligne. Version, contrôles distants et statut du push Git
dans `docs/DEPLOYMENTS.md`.

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

## Rafraîchissement local des trois jeux

Le dépôt `../aleaquant-data` conserve les archives FDJ et les révisions dans son
SQLite commun. Installer une fois l'environnement du pipeline :

```sh
python3 -m venv ~/.local/share/aleaquant-pipeline-venv
~/.local/share/aleaquant-pipeline-venv/bin/python -m pip install -r requirements-pipeline.txt
```

```sh
bash tools/refresh_draws.sh --check      # dit seulement où on en est
bash tools/refresh_draws.sh              # ingère, recalcule faits, profils et pages
bash tools/refresh_draws.sh --backfill-keno-facts # rattrape explicitement les 19k faits Keno
# uniquement si une loi d'un grand régime manque : opération explicite à évaluer
bash tools/refresh_draws.sh --build-missing-laws
```

Chaîne : ingestion des trois archives officielles dans le SQLite de `aleaquant-data`
(révisions conservées) → détection des tirages nouveaux ou corrigés → calcul des faits
et profils par régime des trois jeux → pages EuroMillions/Loto et Keno 16/56 → vérification des SHA
de provenance et des mini-histogrammes. Les lois existantes sont contrôlées par leur
schéma, leur taille `C(n,k)` et la masse de chaque distribution. Une loi manquante est
construite automatiquement si son espace est sous le plafond d'énumération ; un régime
plus grand requiert `--build-missing-laws` et ne sera jamais lancé implicitement par
launchd. Les champs manquants déjà connus de 20/70 restent explicités. Keno produit
ses pages 16/56 sont générées en local ; les pages 20/70 restent à construire. Au premier
Le premier passage normal n'amorce que 30 fiches Keno ; ensuite chaque tirage modifié
est recalculé. Le fonds historique a été rattrapé avec `--backfill-keno-facts`, qui force
le calcul complet et contrôle le SHA de chaque fiche avant de mettre à jour le profil.
Cette option reste disponible pour répéter le contrôle. Elle ne génère pas 19 000 pages :
elle génère seulement les 333 pages 16/56 actuellement actives. Les 19 133 anciens
tirages 20/70 restent destinés au rendu à la demande ou par groupes mensuels. Le journal
d'avancement local reprend un calcul interrompu.
Sans nouvelle révision, aucun calcul ni fichier de sortie n'est réécrit.

**Il ne publie rien** : ni commit, ni `wrangler deploy`, ni approbation d'article. La mise
en ligne reste une décision humaine explicite.

Automatisation via launchd, tous les jours à 08 h 12 et 13 h 12 :

```sh
cp tools/com.aleaquant.refresh.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.aleaquant.refresh.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.aleaquant.refresh.plist
tail -f ~/Library/Logs/aleaquant-refresh.log
```

Les versions Python du calcul sont figées dans `requirements-pipeline.txt` ; les URL
des archives et les règles de jeu résident dans `../aleaquant-data/games/*.yaml`.
`tools/refresh.conf` contient les chemins locaux. Vérifier et mettre à jour une URL
lorsque FDJ ouvre une nouvelle période d'archive. Un import hors de l'hôte officiel
est refusé. La mise en ligne reste un lancement manuel de Wrangler après relecture.

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
- Géométries de portefeuilles : aperçu de génération 1 hétérogène (EuroMillions et
  Keno à 30 grilles, Loto démonstratif à 6). La politique des cohortes, familles,
  références éditoriales et pistes différées est dans
  [`docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`](docs/ATLAS-GEOMETRIES-ARCHITECTURE.md).
  Les générations suivantes s'ajoutent comme nouvelles entrées dans `atlas.json`.

Sections ajoutées au site : `#tirages`, `#atlas`, `#geometries`, `#lab` (fichiers `draws.js`, `atlas.css`).
Un tirage précis s'ouvre avec `#EM-26077`.
# aleaquant

## Pipeline de portefeuilles — premier import du 9 octobre 2026

Le catalogue exploratoire `/portefeuilles/`, relié depuis Géométries, importe les
six profils du prototype indépendant. Le nouvel adaptateur
`engine/portfolio_import.py` valide le contrat JSON strict, les 118 grilles et
leurs coûts, recalcule la géométrie par l'évaluateur partagé avec l'Atlas, puis
revérifie exhaustivement quatre garanties conditionnelles. Les 51 portefeuilles
existants et `dist/data/atlas.json` restent conservés. Le dictionnaire actuel
`dist/metrics.json` est référencé par empreinte (34 entrées au contrôle local) ;
les mesures de portefeuille utilisent leur évaluateur existant.

La consultation reprend la présentation du Prompteur du laboratoire : six
grilles par groupe, tableaux complets des 50 numéros et 12 étoiles, sélection
en bleu et or, boutons précédent/suivant et choix direct du groupe. La page
retient le groupe consulté pour chaque portefeuille pendant la session, en
liant cet état à son empreinte de contenu. La liste compacte reste accessible.
Les helpers JavaScript sont vérifiés contre les helpers Python du Prompteur
sur les 118 grilles ; les fichiers du laboratoire sont lus sans modification.

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_import.py \
  --archive prototypes/portfolio-pipeline/aleaquant_pipeline_2026-10-09.zip --check
# Retirer --check pour écrire dist/data/portfolio_pipeline.json uniquement.
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python -m unittest discover \
  -s tests -p 'test_portfolio_*.py' -v
```

L'import utilise l'environnement du pipeline existant, Python 3.14.8 / NumPy
2.5.3 lors de cette vérification. Il n'exécute aucun script de l'archive,
ne relance pas les 500 000 simulations et ne lit aucun historique.
Les estimations Monte-Carlo sont importées avec leurs IC95, leur graine et
`replayed=false` ; leur cohérence arithmétique est contrôlée, leur simulation
n'est pas reproduite. Les garanties sont conditionnelles au pool, conjointes
sur une même grille, et liées à l'empreinte du portefeuille. `certified` porte
sur cette garantie seulement. `0+2` n'est pas un rang gagnant.

Les budgets 45, 50 et 55 € définissent des cohortes séparées. La référence RANDOM
manque dans ces six profils : aucun classement de performance ni résultat
d'optimalité n'est présenté. Mutation/croisement/réparation, pools explicites,
`max_pairwise_overlap`, garantie demandée, checkpoints et reprise de recherche
restent à implémenter. Les paramètres non supportés sont refusés, jamais ignorés.
Les sept noms d'états sont réservés dans le contrat ; ce premier import ne fait
vivre que les états `evaluated` et `certified`, et rejette les entrées invalides.

Les huit fichiers sources sont préservés sans transformation dans
`prototypes/portfolio-pipeline/source-20261009/` avec l'empreinte de l'archive.
Le sidecar conserve les SHA de configuration/contenu/protocole, les nœuds de
profils et d'évaluation, et les liens `generated_from` et `evaluated_by`.
Une nouvelle importation explicite remplace le sidecar ; il ne s'agit pas encore
d'un catalogue de recherche append-only. Aucun déploiement ne résulte de l'import.

## Pipeline opérationnel 1.0 — génération et évaluation locale

La suite du premier import est implémentée dans ce même dépôt, avec le contrat
strict `engine/portfolio_profile_v1.schema.json` et 13 profils enregistrés dans
`configs/portfolios/milestone-v1.json`. Pools explicites ou tirés avec graine,
contraintes obligatoires, objectifs pondérés, limites de recherche et protocole
d'évaluation sont séparés. Le coût utilisé reste distinct du budget maximal.

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_pipeline.py validate
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_pipeline.py run --include-references
# Commandes séparées : generate, evaluate, compare, export.
# evaluate --stop-after-batches 1 permet un arrêt court, puis evaluate reprend.
```

La nouvelle projection `dist/data/portfolio_search.json` est montrée par défaut
dans `/portefeuilles/`, depuis Géométries. Les exemples et résultats historiques
du ZIP restent une source distincte. Le nouveau MC utilise 20 000 tirages
communs indépendants de la génération (graine 2701009), des IC95 Wilson, des
empreintes de contenu/code/protocole et un checkpoint atomique reprenable.
Il réévalue aussi les six références du ZIP, sans réutiliser leurs comptages.
Les comparaisons à pool identique et entre pools différents à budget égal
gardent des références RANDOM et des compromis géométriques non dominés.

Le dictionnaire partagé conserve ses 34 entrées de grilles et reçoit 12 mesures
de portefeuille avec unités, sens et méthode. L'ancien Atlas, les faits et
portefeuilles du laboratoire restent préservés. Les archives de runs sont
append-only ; seul l'index actif est remplacé explicitement lors de l'export.
Une simulation interrompue ne publie aucun résultat final. Une recherche
infructueuse reste `search_exhausted` ; les garanties sont revérifiées sur le
contenu exact et leurs hypothèses, jamais établies par Monte-Carlo.

Le contrat accepte d'autres budgets mais seulement les règles EuroMillions
5/50+2/12 sans options pour ce jalon. Évolution, mutations et croisements sont
encore refusés explicitement ; ils constituent l'étape suivante après ce
jalon. Aucun modèle monétaire ni remboursement de mise n'est simulé.
Contrat, métriques, preuves, persistance et commandes détaillées :
[`docs/PORTFOLIO-PIPELINE.md`](docs/PORTFOLIO-PIPELINE.md).

## Études exécutables de portefeuilles — 9 octobre 2026

Le moteur 1.1 ajoute une entité Étude, des répétitions à graines appariées et
un mode `prototype_greedy` fidèle au score incrémental du ZIP. Les résultats
importés restent des références ; une nouvelle étude construit ses propres
grilles, compare sur un échantillon commun, puis confirme les finalistes
géométriques sur de nouveaux tirages indépendants.

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_study.py validate --study-config configs/studies/minimize-overlap-20x15x5-v1.json
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_study.py run --study-config configs/studies/minimize-overlap-20x15x5-v1.json
```

Le run imprime son dossier unique et sa progression. Une autre configuration
permet une nouvelle étude ; `--run-dir` reprend la même exécution. Les étapes
incomplètes n'exportent pas de confirmation finale. L'Atlas `/portefeuilles/`
garde un sélecteur des études et de leurs exécutions, en plus du pipeline
initial et du ZIP historique. [Contrat, reprise et interprétation](docs/PORTFOLIO-STUDIES.md).

La première configuration fait varier seulement le poids des intersections
de numéros au carré : 0 / 0,35 / 0,7 / 1,4, sur dix graines communes, 20 grilles
et pool explicite 15/5 (40 constructions avant déduplication). Comparaison
20 000 tirages, graine 2810010 ; confirmation 20 000 tirages, graine 2910010.
Les archives de runs sont immuables, sans écraser le premier jalon.

Étude exécutée : `runs/studies/overlap-20261009-v1`, 40 constructions,
38 nouveaux contenus distincts, cinq finalistes confirmés. Les anciennes
grilles ne sont pas réutilisées. L'augmentation du poids diminue en moyenne
la somme des intersections au carré, mais peut dégrader leur maximum et la
couverture : les tableaux de l'Atlas conservent ces compromis sur les dix graines.

## Mutations, sélection générationnelle et croisements

L'extension `engine/evolution/` réutilise les validations, preuves et évaluations
du pipeline. Elle conserve tous les enfants valides et leur filiation, sélectionne
sur la géométrie exacte, puis compare et confirme sur des tirages nouveaux.
Le contrat et la démo bornée sont décrits dans
[Évolution de portefeuilles](docs/PORTFOLIO-EVOLUTION.md).

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/evolve.py run --study-config configs/evolution/overlap-descendants-v1.json
```

Cette commande crée une nouvelle exécution. La source Evolution de l'Atlas et
ses archives sont séparées de l'étude d'ablation figée.

Démo exécutée : trois générations, 24 nouveaux enfants dont huit croisements,
tous réévalués avec les cinq parents sur 5 000 tirages communs ; cinq enfants
confirmés sur 5 000 nouveaux tirages. La population finale conserve les parents
initiaux sur les critères déclarés ; aucune amélioration n'est revendiquée.
