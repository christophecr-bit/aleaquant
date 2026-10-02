# Journal de développement

## 2026-10-02 — services après redémarrage du Mac

- `tools/refresh.conf` v0.3 : chemins dérivés du dépôt, correction du fichier
  introuvable après déplacement sous ~/aleaquant/ ; surcharges conservées.
- `ops/launchd/org.aleaquant.web-preview.plist` : service de preview installé et
  chargé, 127.0.0.1:4173, maquette incluse, démarrage au login et maintien actif.
- Review et tunnel utilisateur opérationnels ; SSH répond sur 22. Ancien service
  cloudflared système conservé en attente de diagnostic administrateur.
- Validation : syntaxe bash/plist, préflight complet, 9 tests pipeline, cinq pages
  locales HTTP 200 et contrôle Access/public. Aucun nouveau déploiement.
- Inventaire, TODO, dette et rapport SERVICES-POST-RESTART-20261002.md mis à jour.

## 2026-10-02 — administration dans la console de review

- PB-014 précisé : six onglets dans le même outil privé, journal commun et
  catalogue des opérations récurrentes sur données, calculs, batchs, revue,
  publication et services locaux. Contrat canonique dans le dépôt agents :
  `docs/ADMIN-CONSOLE-ARCHITECTURE.md`.
- Roadmap, architecture, TODO et dettes reliées à cette note ; séparation des
  validations scientifiques, éditoriales et de déploiement conservée.
- Documentation uniquement ; aucune interface, tâche planifiée ou action payante
  ajoutée. Vérification des liens locaux et des différences Markdown.

## 2026-10-02 — publication des pages après recalcul

- 9 991 pages reconstruites et build figé au commit `c1aa6639b`.
- Worker `054bb2da-c9d1-4788-9213-a3090e243637` publié sur les deux domaines.
- 129 tests + 28 sous-tests ; 20 contrôles HTTP distants conformes.
- Article approuvé préservé, aucun nouveau texte publié ; attente EM-2011053 maintenue.
- Sauvegarde Git distante rétablie pour le dépôt web : push réussi de la livraison.
- Dette de publication des histogrammes clôturée ; Keno 16/56 publié, archives
  20/70 à la demande toujours en dette. Voir DEPLOYMENTS.md et ses manifestes.

## 2026-10-02 — demande de module d’administration des calculs

- Backlog PB-014 : lancer et suivre les batchs depuis une interface privée, sans
  terminal ni intervention de Codex ; complément de la vue de suivi PB-011.
- Dette associée : file persistante locale, reprise adaptée aux batchs, verrous
  partagés avec launchd, logs, comparaisons et protection des faits approuvés.
- Cadrage uniquement ; aucune interface ni exécution supplémentaire réalisée.

## 2026-10-02 — recalcul intégral des fiches des trois jeux

- 29 124 fiches recalculées : EuroMillions 1 985, Loto 7 673, Keno 19 466.
- 650 775 anciens faits et métadonnées inchangés ; seuls les sous-totaux par dizaine
  s'ajoutent. 29 120 fichiers remplacés, 3 déjà conformes.
- EM-2011053 recalculé mais nouvelle version retenue à part jusqu'à revalidation
  de son article approuvé ; l'article reste reconnu. Aucun déploiement.
- `tests/test_facts_generic.py` : distinguer profil descriptif sans historique et
  métrique historique, sans affaiblir le test anti look-ahead du Loto 2008.
- Tests : 129 web +28 sous-tests, 119 agents réussis.
- [Rapport et sauvegardes](RECALCUL-FAITS-TROIS-JEUX-20261002.md).

## 2026-10-02 — recalcul de trois fiches et essai réel du pipeline

- EM-26078, EM-26077 et EM-2004010 : ajout de `F.main.decade_sums`, 88 faits
  précédents et toutes les métadonnées inchangés. Alias latest synchronisé.
- Trois articles générés : deux atteignent READY_FOR_HUMAN ; un refus justifié
  pour raretés abusives. Aucun article approuvé, aucun déploiement.
- `agent/guards.py` : reconnaît « sous-total » au singulier ; régression réelle
  ajoutée dans `tests/test_article_traceability.py`, sans modifier la prose.
- Tests : **129 web (+28 sous-tests), 119 agents** réussis.
- Rapport : [validation du recalcul](VALIDATION-RECALCUL-20261002.md).

## 2026-10-02 — traçabilité publique et témoins de review

- Spécification : [Sources et méthode](ARTICLE-TRACEABILITY.md).
- `agent/article_traceability.py`, `agent/guards.py` : note déterministe, contrôle
  des citations par mesure/composante, nombres par preuve, couvertures du corps,
  fuite des consignes et rareté locale. Régressions C2/C5 figées depuis la review.
- `agent/compose_draw_report.py`, `agent/compose_batch_collect.py` : consignes
  communes, modes direct/batch/import distingués, writer/modèle cohérents,
  sortie témoin séparée via `--out`. Aucun faux marquage batch d'un ancien draft.
- `agent/editorial_polish.py`, `agent/draw_report.py`, `scripts/import_article.py` :
  note et références revérifiées avant validation/import ; approbation invalidée
  après révision. `engine/build_pages.py`, `dist/app.js` : note et volet dépliable.
- Dépôt agents : schémas typés, pont vers les contrôles web, review de la note et
  politique partagée avec les quatre rôles de rédaction/relecture.
- Tests : **128 web + 28 sous-tests, 119 agents**. 16 régressions web et 5 agents
  ajoutées ; deux générations réelles séparées des tests. Aucun déploiement.
- Métrique `decade_sums` : disponible dans moteur/prompt, absente de l'ancienne
  fiche témoin ; rattrapage des snapshots laissé explicite dans la dette.

## 2026-10-02 — convergence des générateurs de facts sur YAML

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/facts_generic.py`, `engine/build_data.py`, `tools/refresh_draws.py` | Le générateur YAML commun accepte EuroMillions en plus du Loto et du Keno. Le refresh l'utilise pour les trois jeux ; `build_data.py --legacy-facts` conserve explicitement l'ancien chemin EuroMillions comme oracle/rollback. Le constructeur historique n'est pas supprimé. Les facts déjà produits ne sont pas réécrits si le SHA de la source est inchangé ; `--force` permet une régénération délibérée. | Parité JSON complète des 1 985 facts EuroMillions contre `dist` après exclusion des seuls nouveaux `F.main.decade_sums` des deux côtés ; 21 tests ciblés passent. Pas de refresh réel, commit, push ou déploiement. |
| `tests/test_facts_generic.py`, `tests/test_refresh_pipeline.py` | Ajoute le test de parité intégrale des snapshots et vérifie le routage du pipeline commun ainsi que la préservation des facts à source inchangée. | Tests ciblés : 21 réussis ; suite complète web : 111 tests réussis. |
| `docs/TECHNICAL-DEBT.md`, `../../aleaquant-architecture/ARCHITECTURE.md` | Remplace la dette de conception par les tâches restantes de qualification réelle, période d'observation et décision ultérieure sur le retrait du rollback. | Relecture du périmètre, de l'état implémenté et des frontières roadmap/dette. |

## 2026-10-02 — premières pages locales Keno 16/56

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/build_pages.py` | Ajoute les pages par `draw_id`, index, sitemap et présence du Keno actif 16/56 dans le sélecteur. Les 333 faits 20/70 restent archivés sans page ; les JSON de faits demeurent exclus des assets Worker. Les cases des métriques de répartition détaillent leurs bornes pour les trois jeux. | Build local : 1 985 EuroMillions, 7 673 Loto et 333 Keno ; URL Keno 16/56 répond 200, ancien ID 20/70 absent ; budget local inférieur à 20 000 assets. |
| `tools/refresh_draws.py`, `tests/test_refresh_pipeline.py` | Le rafraîchissement vérifie la page Keno active après calcul, sans exiger de page pour 20/70. | Tests pipeline ciblés ; aucun commit ni déploiement. |
| `tests/test_loto_pages.py`, `dist/.assetsignore`, `docs/SCALING.md`, `docs/TECHNICAL-DEBT.md` | Couvre histogrammes, distinction entre probabilité du tirage et gain d'une grille, tranche partielle Keno et décision transitoire de publication. La dette restante porte sur le rendu à la demande des 19 133 anciens tirages 20/70 et la vérification publique. | Tests de pages et budget d'assets ; dry-run Wrangler sans téléversement. |

## 2026-10-02 — pilotage quotidien, RSS public et newsletter hebdomadaire

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/PRODUCT-BACKLOG.md` | Ajoute PB-011 (console « Suivi » et brief privé quotidien), PB-012 (RSS des publications) et PB-013 (newsletter hebdomadaire avec inscription volontaire). Distingue ces fonctions des flux RSS internes de veille. | Relecture des critères de sortie et de la séparation privé/public. |
| `docs/ROADMAP.md`, `docs/SITE-EDITORIAL-ARCHITECTURE.md`, `../aleaquant-editorial-agents/docs/roadmap-editorial-agentique.md` | Définit les blocs du tableau de suivi, les états par jeu et article, les métriques Cloudflare, leur fraîcheur et les garde-fous de diffusion ; prévoit le brief email matinal avec choix du prestataire à cadrer et relie le besoin à la console de review canonique. | Références Cloudflare officielles consultées ; `git diff --check`. |

## 2026-10-02 — consignes SEO Writer et découverte web Scout

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/SEO-EDITORIAL-CHECKLIST.md`, `docs/PRODUCT-BACKLOG.md`, `docs/ROADMAP.md` | Ajoute une checklist SEO datée d'après les sources officielles Google et une capacité produit de précontrôle avant campagne éditoriale ; distingue pages de données et articles narratifs. | Liens vers les références Google Search Central ; relecture de la séparation backlog/roadmap/dette. |
| `../aleaquant-editorial-agents/constitution/seo-editorial.md`, `agent/compose_draw_report.py`, `../aleaquant-editorial-agents/aleaquant/agents/backend.py` | Partage les consignes SEO en une source commune injectée aux Writers batch et LangGraph, sans demander du HTML libre ni modifier les preuves. | Tests Writer SEO ciblés dans les deux dépôts. |
| `../aleaquant-editorial-agents/aleaquant/prompts/scout.md`, `../aleaquant-editorial-agents/docs/roadmap-editorial-agentique.md` | Documente le protocole de recherche critique souhaité et constate que le Scout actuel ne dispose pas d'un outil web ; ajoute PB-010 pour l'adaptateur remplaçable. | Inspection du graphe : le Scout reçoit actuellement les sources du payload, sans recherche réseau. |

## 2026-10-02 — backlog produit, TODO opérationnelle et inventaire technique

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/PRODUCT-BACKLOG.md` | Crée un registre priorisé des résultats produit, distinct de la roadmap descriptive, de la dette et des tâches d'instruction. | Confrontation aux fonctions déjà inscrites dans `ROADMAP.md`, aux décisions d'architecture et aux prototypes existants. |
| `docs/OPERATIONAL-TODO.md`, `docs/TASKS.md`, `docs/ROADMAP.md` | Sépare les opérations récurrentes/ponctuelles des explorations et relie chaque registre à son usage. | Vérification des liens internes et absence de confusion avec la dette technique. |
| `docs/COMPONENT-INVENTORY.md`, `docs/inventory/homebrew-*.txt` | Documente les dépôts, runtimes, paquets, bases SQLite, ports, services macOS et hébergement ; exclut les valeurs de secrets. | Observation lecture seule des versions, tables SQLite et sockets d'écoute ; `git diff --check`. |
| `tests/test_refresh_pipeline.py` | Met à jour l'attendu du régime Keno 16/56 après l'import d'un 333e tirage. | Suite complète : 104 tests réussis. |
| `../aleaquant-editorial-agents/aleaquant/review_console.py`, `tests/test_review_console.py`, `docs/TECHNICAL-DEBT.md` | Reconnaît le préfixe jeu/date du titre comme métadonnée source dans le contrôle numérique des corrections ; conserve le blocage des nombres nouveaux dans le texte. Ajoute le raccord Studio à la dette après inspection. | Suite LangGraph éditoriale complète : 108 tests réussis ; compilation des deux graphes vérifiée sans appel LLM. |

## 2026-10-02 — registre des versions du modèle AleaQuant

| Fichier | Changement | Vérification |
|---|---|---|
| `../aleaquant-data/docs/MODEL-CHANGELOG.md` | Définit un registre inter-dépôts et une mini note publique pour les métriques, claims de méthode, règles/régimes, moteurs et corrections, avec compatibilité, portée recalculée, preuves et approbation. Le point de départ 0.1.0 sera déclaré au gel du MVP ; aucun historique non vérifié n'est inventé. | Relecture du contrat de versionnement et des catégories ; lien depuis roadmap, backlog et TODO. |
| `docs/PRODUCT-BACKLOG.md`, `docs/ROADMAP.md`, `docs/OPERATIONAL-TODO.md`, `docs/TECHNICAL-DEBT.md` | Ajoute PB-008 et le processus opérationnel, puis suit séparément le composant de publication publique. | Distinction vérifiée entre capacité souhaitée, tenue du registre et générateur de note. |

## 2026-10-02 — inspection des graphes dans LangGraph Studio

| Fichier | Changement | Vérification |
|---|---|---|
| `../aleaquant-editorial-agents/pyproject.toml`, `langgraph.json`, `aleaquant/studio.py` | Ajoute le CLI local optionnel 0.4.32, deux entrées Studio et un backend factice sans appel LLM par défaut. | `langgraph validate` détecte les deux graphes ; API locale `/assistants/search` renvoie `editorial_committee` et `draw_publication`. |
| `../aleaquant-editorial-agents/README.md`, `docs/TECHNICAL-DEBT.md`, `docs/COMPONENT-INVENTORY.md` | Documente l'installation, l'ouverture Studio, le mode mémoire et le port local ; ferme l'item de dette. | `langgraph dev --no-browser --host 127.0.0.1` démarre sur `127.0.0.1:2024`. |

## 2026-10-02 — proposition de contenu MVP pour la homepage

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/SITE-EDITORIAL-ARCHITECTURE.md` | Ajoute une proposition de homepage plus courte et une fiche pour chacun des 10 exemples visibles : synopsis, notions à définir, complexité de production, intérêt AleaQuant et destination proposée. | Confrontation à `prototypes/editorial-home/index.html` et au manifeste de lancement éditorial. |
| `docs/TASKS.md` | Passe le cadrage des rubriques et cartes au statut « proposition formulée — validation à venir ». | Vérification de la séparation entre décision éditoriale, roadmap produit et dette technique. |
| `engine/build_pages.py`, `agent/guards.py`, `agent/draw_report.py`, `agent/prompts/editorial_angle.md`, `scripts/import_article.py`, `tests/test_loto_pages.py`, `tests/test_editorial_angle.py`, `tests/test_import.py` | Les titres publiés des analyses identifient le jeu et la date ; l'accroche A/B/C est conservée après ce contexte ; l'import refuse un titre incomplet. | Tests ciblés EuroMillions/Loto et import sans appel API. |
| `../aleaquant-editorial-agents/constitution/editorial-style.md`, `aleaquant/prompts/writer.md`, `aleaquant/tools/checks.py`, `aleaquant/graph/draw_publication.py`, `tests/test_draw_publication.py` | Propage la règle dans la constitution, le prompt Writer et un contrôle déterministe du checkpoint de publication. | `.venv/bin/pytest -q tests/test_draw_publication.py`. |

## 2026-10-01 — séparation roadmap produit et dette technique

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/ROADMAP.md`, `docs/SITE-EDITORIAL-ARCHITECTURE.md`, `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md` | Centralise les fonctions attendues du site, de l'application éditoriale responsive et de l'Atlas ; précise la publication humaine avec choix de rubrique. Les notes d'architecture conservent contrats et invariants, pas de todolist. | Relecture contre les architectures détaillées et le backlog du comité. |
| `docs/TECHNICAL-DEBT.md` | Retire l'inventaire des travaux terminés, sujets éditoriaux, objectifs de recherche et décisions d'architecture ; ne conserve que des composants d'ingénierie, validations et tâches d'exploitation actionnables. | `git diff --check` et vérification des liens vers les documents de référence. |
| `docs/TASKS.md`, `docs/HANDOFF.md` | Crée un registre limité aux explorations et coordinations ponctuelles ; remplace la vieille todolist figée du handoff par des pointeurs vers les registres actifs. | Contrôle des destinations et absence de doublon avec roadmap et dette. |
| `../aleaquant-editorial-agents/docs/roadmap-editorial-agentique.md`, `../aleaquant-editorial-agents/docs/TECHNICAL-DEBT.md` | Ajoute à la roadmap du comité la publication avec rubrique après validation SHA et sépare ses composants restants dans une dette dédiée. | Relecture du flux humain et des frontières entre dépôts. |
| `../aleaquant-editorial-agents/docs/editorial-launch-manifest.md`, `../aleaquant-editorial-agents/docs/editorial-topics/multiplicite-tests-benjamini-hochberg.md` | Ajoute une proposition éditoriale sur la multiplicité des tests, le taux de fausses découvertes, BH et la dépendance entre métriques. | Vérification du périmètre par les articles primaires de Benjamini–Hochberg (1995) et Benjamini–Yekutieli (2001). |

## 2026-10-01 — rattrapage du fonds historique Keno

| Fichier | Changement | Vérification |
|---|---|---|
| `tools/refresh_draws.py`, `tools/refresh_draws.sh` | Option explicite `--backfill-keno-facts` pour recalculer toutes les fiches Keno à partir du SQLite, vérifier leur SHA, puis reconstruire le profil. Le préflight expose le nombre de faits Keno valides au lieu de confondre l'état des archives et celui des faits. | Exécution réelle : 19 465 fiches calculées en 9 s ; 19 465/19 465 SHA vérifiés ; aucun commit/déploiement. |
| `engine/rarity_profiles.py` | Corrige le glob des préfixes `KE-`/`LO-`/`EM-` qui ajoutait un second tiret et produisait des profils vides. En-tête version/date/auteur/historique/TODO ajouté. | Profils reconstruits : EM 20+6 métriques, Loto 20+20, Keno 20 en 16/56 et 17 en 20/70. |
| `tests/test_refresh_pipeline.py` | Vérifie le backfill forcé même si l'état source semble à jour, la couverture SHA et la présence des deux régimes dans le profil Keno. | 8 tests pipeline ; suite web complète : 103 tests réussis. |
| `README.md`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md`, `docs/SCALING.md`, `../../loto-keno-lab/docs/pipelines-et-graphes.md` | Distingue le retard de faits, maintenant résorbé, du chantier des pages Keno à la demande/groupées et refuse 19 465 assets HTML supplémentaires. | Relecture du cycle réel et des nombres de fiches/profils. |

## 2026-10-01 — mini-histogrammes alignés sur la homepage

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/build_pages.py` | Les pages de tirage utilisent maintenant une barre SVG par classe, comme la sparkline de l'accueil. Suppression du regroupement au-delà de 48 classes ; loi, hauteur minimale visible et marqueur orange inchangés. Texte de légende corrigé. | Test dédié : nombre de barres égal au nombre de classes ; 9 658 pages régénérées ; tests EuroMillions/Loto. |
| `tests/test_loto_pages.py` | Test de non-régression du nombre de classes dessinées et maintien du marqueur/du pixel minimal. En-tête auteur/version/historique/TODO ajouté. | Suite complète des tests web. |
| `README.md`, `docs/TECHNICAL-DEBT.md`, `docs/CHANGELOG.md` | État local distingué de la publication ; dette de cohérence supprimée après validation et attente de déploiement explicitée. | Relecture documentaire et `git diff --check`. |

## 2026-10-01 — piste d'archive tabulaire résultats + faits

| Fichier | Changement | Vérification |
|---|---|---|
| `docs/SITE-EDITORIAL-ARCHITECTURE.md` | Ajoute une proposition de vue historique tabulaire pour explorer et réutiliser les données : filtres jeu/régime, tri, pagination, export CSV/JSON documenté. La reporte après le rendu Keno à la demande ; aucune interface ni export encore implémenté. Corrige aussi la documentation des mini-histogrammes pour refléter une barre par classe. | Relecture de la portée par rapport aux archives, profils, règles et plafond d'assets. |
| `docs/TECHNICAL-DEBT.md` | Inscrit le cadrage de l'archive données après la route Keno, avec exigences de provenance, taille et version. | Cohérence avec `SCALING.md` et l'état actuel du moteur. |

## 2026-10-01 — sujet éditorial international sur les loteries k parmi C

| Fichier | Changement | Vérification |
|---|---|---|
| `../aleaquant-editorial-agents/docs/editorial-launch-manifest.md`, `docs/editorial-topics/loteries-k-sur-c.md` | Sujet rangé dans le manifeste du comité éditorial, avec synopsis, questions, plan, preuves officielles à réunir et distinctions entre tirage sans remise, modèle uniforme et indépendance temporelle. | Relecture des garde-fous de méthode ; exemples de jeux à documenter avant toute affirmation comparative. |
| `docs/SITE-EDITORIAL-ARCHITECTURE.md`, `docs/TECHNICAL-DEBT.md` | La roadmap du site pointe vers le brief éditorial canonique ; l'entrée a été retirée de la dette technique. Le cadrage de l'archive résultats + faits reste dans la roadmap produit. | Vérification des destinations et de la séquence de dépendances. |

## 2026-10-01 — lois et profils raccordés au rafraîchissement des trois jeux

| Fichier | Changement | Vérification |
|---|---|---|
| `tools/refresh_draws.py`, `tools/refresh_draws.sh` | Avant ingestion, vérifie les lois de chaque régime déclaré : schéma, `C(n,k)`, index des champs et masse de chaque distribution. Construit les petits régimes absents ; les grands régimes absents exigent `--build-missing-laws`. Après recalcul des faits, produit le profil par régime EuroMillions, Loto ou Keno. En-têtes de version/historique/TODO actualisés. | 5 tests dédiés au rafraîchissement ; `bash tools/refresh_draws.sh --check` réussi sans ingestion. |
| `tests/test_refresh_pipeline.py` | Régressions de masse/total des lois et présence des profils Keno/EuroMillions dans le flux. | `python3 -m unittest tests/test_refresh_pipeline.py -v` : 5 tests réussis. |
| `README.md`, `docs/TECHNICAL-DEBT.md`, `docs/HANDOFF.md`, `../../loto-keno-lab/docs/pipelines-et-graphes.md` | Étapes réelles distinguées des dettes restantes ; graphe pipeline actualisé, workflow rédactionnel court et cible de console responsive privée décrits après la validation des faits. | Vérification des liens et `git diff --check`. |


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

## 2026-10-01 — intégration locale des lois Keno 16/56

| Fichier | Changement | Vérification |
|---|---|---|
| `engine/keno-laws-metal-exact-16-56.json`, `engine/laws_recurrence.py` | Artefact Metal exact validé et intégré au générateur 16/56. | Sommes exactes, couverture complète, 9 tests lois/récurrences. |
| `dist/data/laws/regime-16-56.json`, `dist/data/facts/KE-*.json`, `dist/data/rarity_profiles/keno.json` | 20 lois, 31 faits Keno et profil de rareté recalculés localement. | 9 tests de faits génériques; aucun déploiement. |
| `tests/test_laws.py`, dettes et handoff | Contrat 16/56 actualisé; comparaison Rayon exhaustive et qualification des pages maintenues en dette. | 18 tests ciblés réussis. |

## 2026-10-02 — sous-totaux des numéros par dizaine

| Fichier | Changement | Vérification / impact |
|---|---|---|
| `engine/metrics.py`, `engine/facts.py`, `engine/facts_generic.py` | Ajout de `F.main.decade_sums`, vecteur déterministe montrant pour chaque dizaine l'effectif et la somme de ses valeurs. Commun à EuroMillions, Loto et Keno, sans classe ni rareté. | Cas tests 5/50, 5/49, 16/56 et 20/70. Aucun fichier de loi probabiliste ajouté. |
| `engine/build_pages.py`, `dist/atlas.css`, `dist/metrics.json`, `dist/index.html` | Carte dédiée aux sous-totaux sur les fiches des trois jeux ; affichage D1, D2… sans répéter les bornes numériques. | 9 991 fiches existantes reconstruites, sans nouveau fichier par métrique ni réécriture des faits historiques. Les deux URL distantes vérifiées renvoient HTTP 200 et affichent la carte. |
| `agent/guards.py`, `agent/draw_report.py`, prompts et tests | Mise à disposition du profil au Writer en français lisible ; garde-fous qui le distinguent des métriques classées par une loi. | 110 tests réussis. Déploiement Wrangler 4.147.0 : version `2a0f4c85-c06c-4b59-917e-e8f75da15e43`. Taille mesurée : environ 773 octets de HTML par fiche en moyenne ; calcul local de profil environ 3,1 µs par entrée. Vérifier l'utilité éditoriale avant d'envisager une loi marginale. |
