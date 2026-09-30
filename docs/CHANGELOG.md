# Journal de développement

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
