# Journal de développement

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
