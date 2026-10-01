# Journal de développement

## 2026-10-01 — proposition CI et environnement de recette

Ajout de `docs/CI-STAGING-PRODUCTION.md` après vérification de la documentation
Cloudflare Workers actuelle. Recommande un Worker persistant de recette protégé
par Access, une promotion production soumise à approbation, et distingue jeton
du tunnel, identité d’accès et clé API CI. Dette et handoff reliés. Proposition
documentaire uniquement : aucun workflow ou Worker de recette activé.

## 1er octobre 2026 — domaine aleaquant.org

Domaine actif chez Cloudflare, raccordé par Custom Domain au Worker `aleaquant`.
Site : https://aleaquant.org/ ; maquette : https://aleaquant.org/maquette/.
Aucun asset redéployé : version existante conservée. HTTPS vérifié (HTTP 200),
accueil, maquette et `/tirages/loto/LO-20260928/` identiques octet pour octet
à workers.dev. Route persistée dans `wrangler.jsonc`, workers.dev conservé.
Le terminal distant Cloudflare Access/Tunnel n’est pas encore configuré.


## 2026-10-01 — mise en ligne vérifiée de la maquette et des graphes

Worker `18285622-994a-42cc-9e0f-937b28c67f7a`, 9 691 assets issus du commit
`deedfc645`. Maquette sous `/maquette/` ; trois pages contrôlées avec 18/21/18
mini-histogrammes et comparaison des réponses à l'export Git. Quatre tests de
pages réussis. README, architecture, dette et handoff actualisés. Le push Git
reste bloqué par l'accès au trousseau macOS ; détails dans `DEPLOYMENTS.md`.

## 2026-10-01 — préparation de la maquette consultable à distance

`prototypes/editorial-home/index.html` et sa copie `dist/maquette/` exposent un
aperçu public explicitement signalé, avec données datées et noindex. L'accueil
actuel est conservé ; les pages de tirage corrigées font partie du prochain
déploiement. Pour resynchroniser l'aperçu : copier `index.html` et `assets/`
du prototype dans `dist/maquette/`. Déploiement et vérification réseau à suivre.

## 2026-10-01 — sujet éditorial HPC en combinatoire

Ajout de `docs/research/sujet-editorial-hpc-combinatoire.md` : angle, trois titres,
plan court, sources de preuve, figure et conditions de relecture. Dette et
handoff reliés au brief. Documentation seule, liens vérifiés ; aucun article publié.

## 2026-10-01 — capitalisation des algorithmes HPC pour l'Atlas

La note versionnée `../loto-keno-lab/docs/CAPITALISATION-HPC-ATLAS.md` rassemble
sources B3, Gray/Algorithm R, colex, SWAR/NEON, benchmarks et limites, pistes
B1/B2 écartées et qualification du worker durable. Architecture, dette et
handoff pointent vers cette référence ; adaptation des tailles et jeux à
qualifier. Liens locaux et diff vérifiés ; documentation seule, aucun benchmark
relancé, moteur modifié ou déploiement.

## 2026-10-01 — premier certificat de garantie conditionnelle pour l'Atlas

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/conditional_guarantees.py`, `tools/solve_conditional_wheel.py`, `docs/research/conditional-wheel-10-5-4-3.json` | Vérificateur exhaustif indépendant, constructeur glouton et pilote MILP facultatif ; `3 if 4 of 10` Loto résolu à 7 grilles minimum (borne du solveur 7, écart nul). Ce résultat porte seulement sur les numéros principaux. | 210 scénarios contrôlés ; solution archivée avec empreintes ; 8,452 s lors de l'essai. |
| `tests/test_conditional_guarantees.py` | Cas de certification, contre-exemple, borne de comptage, renommage, limites de calcul et vérification indépendante de la solution archivée. | Suite de tests du projet. |
| `docs/research/garanties-conditionnelles-portefeuilles.md`, `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md` | Les garanties deviennent un axe de recherche ciblé de l'Atlas ; roues personnalisées et vente de calcul restent différées. Le coût des mises et la faiblesse possible des petits rangs sont explicites. | Cohérence du contrat et des limites éditoriales. |

## 2026-10-01 — recentrage de l'Atlas sur son objectif initial

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`, `docs/research/garanties-conditionnelles-portefeuilles.md`, `docs/TECHNICAL-DEBT.md`, `docs/SITE-EDITORIAL-ARCHITECTURE.md`, `docs/HANDOFF.md`, `README.md` | Atlas v0.1 limité aux références éditoriales et à leur géométrie ; roues conditionnelles et optimisation personnalisée reportées ; aucune vente de compute ou parcours de paiement prévu. Les entrées du journal ci-dessous conservent l'historique des pistes explorées, pas la feuille de route active. | Contrôle de cohérence documentaire ; aucun calcul, service ou déploiement. |

## 2026-10-01 — garanties conditionnelles de portefeuilles

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/research/garanties-conditionnelles-portefeuilles.md`, `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md` | Formalisation de `x if y of p`, preuve exhaustive et contre-exemple, distinction nombre de correspondances/rang, exemple Loto pool 10 / 25 grilles et études à mener. | Convention vérifiée sur Lottery Post ; borne `4 if 4 of 10` calculée ; pas de moteur ni garantie publiés. |

## 2026-10-01 — contribution éventuelle aux calculs personnalisés

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`, `docs/TECHNICAL-DEBT.md` | Accès libre aux solutions déjà calculées ; contribution modeste envisageable uniquement pour une recherche nouvelle, bornée et annoncée avant lancement ; aucun tarif ou paiement activé. | Recherche de politique existante dans les documents et contrôle du diff. |

## 2026-10-01 — optimisation différée et hébergement

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md` | Parcours de demande différée : statut durable, calcul local reprenable, revue du résultat et courriel facultatif ; Cloudflare Containers à mesurer avant adoption. | Tarifs et limites vérifiés dans la documentation officielle Cloudflare ; aucune ressource ni envoi créé. |

## 2026-10-01 — correction de la politique de précalcul de l'Atlas

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`, `docs/SITE-EDITORIAL-ARCHITECTURE.md`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md`, `README.md` | Distinction entre mesure rapide d'un portefeuille fourni et recherche combinatoire hors ligne ; matrice de paramètres à précalculer, dont Loto pool 10 / 25 grilles ; 6 et 30 ne sont que les tailles déjà montrées. | Confrontation aux générateurs Keno et au calcul de géométrie Loto existants ; aucune implémentation ou publication. |

## 2026-10-01 — demande Atlas d'une taille libre

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`, `docs/TECHNICAL-DEBT.md` | Cas concret de 20 grilles : génération ou apport des grilles, géométrie immédiate, référence RANDOM de même taille, calcul de gain séparé ; distinction entre commande locale future et interface publique encore absente. | Relecture du contrat avec le site statique actuel et les métriques du laboratoire. |

## 2026-10-01 — architecture de l'Atlas des géométries

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md` | Contrat commun, cohortes par règle/format/budget, tailles repères 6 et 30, Loto à qualifier, Keno 10-numéros d'abord, géométrie à la demande et évaluations hors ligne. | Inventaire de `dist/data/atlas.json`, des catalogues et du dictionnaire du laboratoire ; relecture des liens et du diff. |
| `README.md`, `docs/SITE-EDITORIAL-ARCHITECTURE.md`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md` | Pointeurs d'architecture et tâches ouvertes alignés ; ancienne limite documentaire des histogrammes corrigée ; aucune modification des calculs ni du Worker. | Contrôle documentaire. |

## 2026-09-30 — cohérence des histogrammes de tirage

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/build_pages.py`, `tests/test_loto_pages.py` | Toutes les métriques scalaires dont la loi correspond au fait ont un mini-histogramme ; queue non nulle visible sur un pixel ; les signatures non ordonnées restent textuelles. | Test de régression `LO-20260928` : 18 graphes, bonne loi 5/49 et refus de la loi 5/50. |
| `dist/tirages/{euromillions,loto}/**/index.html`, `README.md`, `docs/HANDOFF.md`, `docs/TECHNICAL-DEBT.md` | 9 658 fiches locales régénérées et état documenté ; aucun déploiement. | Inspection visuelle locale, suite web complète. |

## 2026-09-30 — collecte et calcul enchaînés pour trois jeux

| Fichier | Changement | Vérification |
|---|---|---|
| `tools/refresh_draws.py`, `tools/refresh_draws.sh`, `tools/refresh.conf`, `tools/com.aleaquant.refresh.plist`, `requirements-pipeline.txt` | Ingestion EuroMillions/Loto/Keno avant calcul, journal d'avancement, reprise, contrôle de provenance ; deux passages quotidiens planifiés ; environnement Python figé. Keno reste local sans page. | Préflight, cycle réel, reprise simulée et passage idempotent. |
| `engine/common.py`, `tests/test_refresh_pipeline.py` | Filtre EuroMillions sur le SQLite commun ; régressions d'ordre des étapes et d'échec sans avancement. | Suite web complète. |
| `dist/data/**`, `dist/tirages/**`, `dist/sitemap.xml` | Faits locaux des nouveaux Loto/Keno et pages EuroMillions/Loto recalculées ; pas de déploiement. | SHA des sources, mini-histogrammes et contrôle des pages. |
| `README.md`, `docs/HANDOFF.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Contrat de collecte, état réel et dette Keno mis à jour. | Relecture et suite de tests. |

## 2026-09-30 — gabarit de rubriques et retour des graphes de tirage

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/build_pages.py`, `dist/tirages/{euromillions,loto}/**/index.html` | Lois exactes du régime rendues en mini-histogrammes SVG pour six mesures pertinentes au plus ; trait orange sur la valeur observée, légende de regroupement visuel ; 9 657 pages régénérées localement, sans déploiement. | Échantillons EuroMillions et Loto, actuels et historiques ; comptage de toutes les pages. |
| `tests/test_loto_pages.py` | Régression des graphes et refus d'une loi d'un autre régime. | Suite web complète. |
| `prototypes/editorial-home/index.html`, `docs/SITE-EDITORIAL-ARCHITECTURE.md` | Quatre rubriques, huit cartes de contenus clairement typées, sujets non publiés sans lien ; gabarit et prochain chantier documentés. | Inspection desktop/mobile de la maquette locale. |
| `README.md`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md`, `docs/CHANGELOG.md` | État, dette et reprise alignés sur la maquette et le correctif local. | Relecture des statuts et des liens. |

## 2026-09-30 — covariance historique par jeu et régime

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/order_position_history.py`, `tests/test_order_position_history.py` | Lecture seule des dernières révisions ; matrices observées avec diviseur `m−1`, groupes séparés par jeu/règle, fenêtre rétrospective et empreinte de cohorte. | Tests de séparation, de révision corrigée, de fenêtre et de l'identité de variance de l'étendue. |
| `docs/research/covariance-historique-par-jeu.md`, `docs/research/order-position-history-2026-09-30.json`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md`, `docs/CHANGELOG.md` | Sept groupes locaux documentés, Keno à rafraîchir, aucune inférence statistique ni publication. | Rapport régénéré depuis la base source et suite web complète. |

## 2026-09-30 — covariance théorique des positions ordonnées

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/order_position_covariance.py`, `tests/test_order_position_covariance.py` | Moments exacts par régime et identité de variance de l'étendue, avec `game_id` explicite et refus d'une association jeu/régime invalide, sans donnée historique ni effet sur les pages. | Toutes les cellules comparées à l'énumération de petits univers ; étendue recoupée avec la loi exacte des régimes 5/50 et 16/56. |
| `docs/research/covariance-positions-ordonnees.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Résultats, source primaire et limites consignés ; audit futur séparé par jeu, composante et régime ; dette recentrée sur l'historique et l'article. | Documentation relue et suite complète. |

## 2026-09-30 — convention proposée pour la covariance des positions

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Deux entrées candidates de registre, théorique et historique, avec libellés et métadonnées minimales ; aucune métrique activée. | Cohérence avec le registre versionné existant et avec la distinction établie par Coronel-Brizio et al. |

## 2026-09-30 — piste de recherche sur la covariance

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md`, `docs/CHANGELOG.md` | Source Coronel-Brizio et al. référencée ; covariance des positions d'un tirage distinguée de l'autocovariance temporelle ; audit par régime, rapport à l'étendue et article de fond inscrits comme travaux à qualifier. | Lecture de l'article arXiv 0806.4595 ; documentation seule, aucun calcul ou contenu publié. |

## 2026-09-30 — article associé à chaque page de tirage

| Fichier | Changement | Vérification |
|---|---|---|
| `scripts/import_article.py`, `engine/build_pages.py` | Association unique par `draw_id`, contrôle du SHA des faits, rendu du récit approuvé dans la page du tirage, rafraîchissement ciblé à l'import. | Tests d'import et de pages ; suite web complète. |
| `dist/atlas.css`, `dist/tirages/euromillions/2011-09-06/index.html` | Présentation du récit et premier article historique sur sa page canonique. | Inspection du HTML local. |
| `tests/test_import.py`, `tests/test_loto_pages.py`, `README.md`, `docs/HANDOFF.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Régressions d'identité, de non-publication des brouillons, de rattachement et de rendu échappé ; état et dette mis à jour. | Suite web complète. |

## 2026-09-30 — configuration du batch depuis les agents

| Fichier | Changement | Vérification |
|---|---|---|
| `agent/compose_batch_submit.py`, `agent/compose_batch_collect.py` | Options facultatives de modèle, effort, fenêtre et empreinte du profil ; SHA des faits et du prompt dans le manifeste ; collecte refusée si les faits ont changé ; modèle réel dans la provenance et SHA recalculé si le Writer change ; estimation de coût suspendue sans tarif connu ; fichier de soumission refermé après l'envoi. Les valeurs par défaut et les anciens manifestes restent utilisables. | Test d'envoi simulé sans API, test de collecte hors API, suite web. |
| `tests/test_compose_batch_config.py`, `README.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Régression de provenance et documentation du graphe court situé dans le dépôt canonique des agents. | Suite web complète. |

## 2026-09-30 — angles A/B/C et relecture éditoriale contrôlée

| Fichier | Changement | Vérification |
|---|---|---|
| `agent/prompts/editorial_angle.md`, `agent/editorial_angle.py` | Compétence de rédacteur en chef : trois angles référencés par faits, contrôle des titres, révision et choix humain liés aux empreintes des propositions et des faits. | Essai réel EM-26078 et tests hors API. |
| `agent/compose_draw_report.py`, `agent/guards.py` | Angle et style appliqués seulement à l'essai direct qui reçoit `--angle` ; répare aussi deux imports manquants (`ENV_PATH`, `repair_prompt`). Le batch conserve son prompt de base et ne lit pas les angles. | Brouillon EM-26078 en attente humaine ; test d'indépendance du batch. |
| `agent/prompts/editorial_polish.md`, `agent/editorial_polish.py` | Relecture de fluidité sur un brouillon séparé : conserve nombres, rareté, paragraphes et faits cités, puis recalcule le SHA. | Essai EM-26078 et régressions hors API. |
| `scripts/import_article.py`, `tests/test_guards.py`, `tests/test_editorial_angle.py`, `tests/test_editorial_polish.py` | Le titre rejoint le contrôle anti-prédiction à l'import ; tests A/B/C, provenance, indépendance du batch, décades, relecture et empreintes. | Suite web complète. |
| `requirements-dev.txt`, `.gitignore`, `README.md`, `docs/HANDOFF.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Dépendances explicites, sorties locales ignorées, mode d'emploi, état réel et évaluation restante. | 77 tests réussis dans l'environnement avec PyYAML 6.0.3 ; le Python système sans PyYAML échoue sur 3 tests de `aleaquant-data`. |

## 2026-09-30 — fil des tirages et feuille de route Atlas

| Fichier | Changement | Vérification |
|---|---|---|
| `prototypes/editorial-home/index.html`, `prototypes/editorial-home/assets/probability-landscape.png` | Deux cartes « derniers tirages » fondées sur les résultats locaux Loto et EuroMillions, titraille plus éditoriale, commentaires plus fluides et image originale générée pour la maquette. | Vérification structurelle des titres, dates, numéros et liens ; aperçu local non publié. |
| `README.md`, `docs/HANDOFF.md`, `docs/TECHNICAL-DEBT.md` | Snapshot et raccordement futur du fil documentés ; Atlas réinscrit avec première version de portefeuilles et articles de fond sur les familles et leur géométrie. | Relecture documentaire. |

## 2026-09-30 — première maquette éditoriale en cartes

| Fichier | Changement | Vérification |
|---|---|---|
| `prototypes/editorial-home/index.html` | Maquette autonome non publiée : cadre général, promesse plus visible, mini-expérience et cartes pour les sujets existants, micro-illustrations vectorielles et adaptation mobile. | Contrôle HTML structurel et inspection locale ; aucune donnée métier modifiée. |
| `README.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Emplacement et statut du prototype documentés ; intégration au site reste en dette active. | Relecture des liens et statuts. |

## 2026-09-30 — pages Loto et fondations Keno

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/build_pages.py` | Pages et index Loto par identifiant, régimes historiques, navigation et sitemap ; pages Euro préservées. | `tests/test_loto_pages.py` et suite web |
| `dist/index.html`, `dist/atlas.css` | Accès au Loto et rendu de ses composantes. | Inspection du HTML généré |
| `dist/.assetsignore` | Faits intermédiaires maintenus dans Git et exclus des assets Cloudflare. | Comptage des fichiers et contrôle Wrangler |
| `engine/laws_recurrence.py`, `engine/laws.py` | 16 lois Keno exactes sans énumération impossible ; champs manquants explicites. | `tests/test_laws_recurrence.py` |
| `engine/facts_generic.py` | Méthode de calcul correcte dans les faits basés sur une récurrence. | Suite web et équivalence Euro |
| `tests/test_loto_pages.py`, `tests/test_laws_recurrence.py` | Non-régression des deux régimes Loto, doubles séances et lois récurrentes. | Suite web |
| `tests/test_asset_budget.py` | Bloque localement un dépassement du plafond de 20 000 assets après exclusion des faits intermédiaires. | Suite web |
| `README.md`, `docs/HANDOFF.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Reprise, déploiement, dettes actives et décisions. | Relecture |

Déploiement vérifié le 30/09/2026 : Wrangler 4.144.0, Worker version
`079f1872-6934-400f-b044-0cf73e09791d`, 7 678 assets nouveaux ou modifiés et
2 008 déjà présents (9 686 au total). Les pages `LO-20081006` et `LO-19920328-2`
répondent en HTTP 200 ; `/data/facts/LO-20081006.json` répond en HTTP 404.
Suite web complète : 60 tests réussis. Le déploiement GitHub → Cloudflare automatique
reste à vérifier ; ce déploiement-ci a été lancé manuellement par Wrangler.

## 2026-09-30 — choix du jeu et croissance des archives

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/build_pages.py`, `dist/index.html`, `dist/atlas.css` | Choix explicite EuroMillions/Loto depuis l'accueil et toutes les pages de tirage ; index commun `/tirages/`. | `tests/test_loto_pages.py` et suite web |
| `docs/SCALING.md` | Décision de ne pas créer 19 452 pages Keno ; conception de groupes mensuels et rendu Worker à la demande, avec critères SEO et de validation. | Limites Cloudflare et comptage local |
| `README.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | Parcours utilisateur et dette de migration mis à jour. | Relecture |

Sélecteur publié le 30/09/2026 : Worker version
`27128adb-e8e6-4ec5-95a3-63d98370b445`, 9 687 assets actifs et URL
`/tirages/` vérifiée en ligne. Suite web complète : 60 tests réussis.

## 2026-09-30 — calendrier Loto et périmètre EuroMillions

| Fichier | Changement | Vérification |
|---|---|---|
| `dist/index.html`, `dist/atlas.css` | Le calendrier de l'accueil est nommé explicitement EuroMillions ; lien direct vers la recherche Loto. | Relecture de la page générée |
| `engine/build_pages.py`, `dist/loto-index.js` | Recherche par date dans l'archive Loto ; deux tirages d'une même date restent deux résultats. | `tests/test_loto_pages.py` |
| `tests/test_loto_pages.py` | Vérifie le champ date et les deux séances du 28/03/1992. | Suite web |

## 2026-09-30 — prototype d'archive Keno compacte

| Fichier | Changement | Vérification |
|---|---|---|
| `prototypes/keno-on-demand/*` | 19 452 tirages réels regroupés en 397 mois, index d'identifiants et route Worker SSR expérimentale ; aucun fichier de tirage individuel dans Git. | `build_shards.py`, `node check.mjs` |
| `docs/SCALING.md`, `docs/TECHNICAL-DEBT.md` | Mesures du prototype et travail restant pour des pages Keno avec faits. | Relecture |

## 2026-09-30 — qualification des faits et lois Keno

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/laws_recurrence.py`, `dist/data/laws/regime-16-56.json`, `regime-20-70.json` | Loi exacte des paires proches ajoutée ; 17 métriques sur 20, trois manquantes explicites. | Petits univers exhaustifs, premier moment indépendant, suite web |
| `engine/facts_generic.py` | `F.draw.probability` pour le tirage Keno exact, séparé du gain d'une grille ; CLI ciblée sans réécrire tout `dist/`. | Quatre tirages réels et suite web |
| `tests/test_laws_recurrence.py`, `tests/test_laws.py`, `tests/test_facts_generic.py` | Totaux Keno, régimes, provenance, antériorité et probabilité correctement nommée. | Suite web |
