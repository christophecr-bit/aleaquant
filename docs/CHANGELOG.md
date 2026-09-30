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
