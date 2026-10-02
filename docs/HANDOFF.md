# AleaQuant — document de reprise (handoff)

Sources de vérité : fonctions dans [`ROADMAP.md`](ROADMAP.md), composants actifs dans
[`TECHNICAL-DEBT.md`](TECHNICAL-DEBT.md), décisions dans les documents d'architecture,
et explorations ponctuelles dans [`TASKS.md`](TASKS.md). Les états datés plus bas
sont des instantanés de reprise et ne remplacent pas ces registres.

État du pipeline données au 01/10/2026 : le rafraîchissement valide les lois des
régimes et recalcule les profils par régime pour EuroMillions, Loto et Keno. Les
19 465 résultats Keno déjà présents en SQLite ont maintenant tous leurs fiches locales
et leur profil : 332 tirages 16/56, 19 133 tirages 20/70. Le prochain retard concerne
le rendu des pages Keno, à la demande ou en groupes mensuels, puis le workflow
rédactionnel court par nouveau tirage (faits validés → brouillon gardé → approbation
humaine → import explicite). Carte et Mermaid :
`../../loto-keno-lab/docs/pipelines-et-graphes.md` ; dette active :
`docs/TECHNICAL-DEBT.md`. La revue mobile envisagée est une console locale responsive
protégée par Cloudflare Access sur Tunnel ; SQLite reste sur le Mac et l'approbation
ne déclenche pas de publication.

> Mise à jour du 02/10/2026 : les 333 fiches Keno du régime actif 16/56 ont maintenant
> un rendu local par identifiant, un index, un sitemap et 20 cartes métriques. Le hub
> local inclut Keno ; les JSON de faits restent exclus du paquet Worker. Les 19 133
> tirages 20/70 n'ont toujours pas de pages. La route publique Keno répond encore 404 :
> aucun déploiement n'a été effectué. Voir `docs/SCALING.md` et `TECHNICAL-DEBT.md`.

> Mise à jour du 01/10/2026 : mini-histogrammes harmonisés localement. Le générateur
> des fiches de tirage dessinait des groupes de classes au-delà de 48, tandis que la
> homepage conservait une barre par classe. Les 9 658 pages EuroMillions/Loto sont
> régénérées avec le même principe de dessin ; 100 tests passent. Cette harmonisation
> reste à publier. Aucun calcul de loi ni effectif n'a changé.

> Rattrapage Keno du 01/10/2026 : option `bash tools/refresh_draws.sh
> --backfill-keno-facts` ; 19 465 fiches calculées en 9 s, provenance SHA vérifiée,
> profils EM/Loto/Keno corrigés et reconstruits. Le fichier de profil avait été vide
> à cause d'un motif `KE--*.json` erroné ; les deux régimes Keno contiennent maintenant
> respectivement 20 et 17 métriques. Aucun calcul massif de lois n'a été relancé.

Politique proposée pour CI, recette et production : `CI-STAGING-PRODUCTION.md`.
Recommandation : Worker `aleaquant-recette` sur `recette.aleaquant.org`, protégé
par Access ; garder `private.aleaquant.org` pour le tunnel Mac. Le jeton du
tunnel, l’API Token CI et l’identité Access ont des rôles distincts. Aucun
pipeline ni recette isolée n’est encore activé.

Domaine raccordé le 01/10/2026 : https://aleaquant.org/ et
https://aleaquant.org/maquette/. HTTPS et trois pages vérifiés ; pas de nouveau
déploiement des assets. Configuration persistée dans `wrangler.jsonc`.
Accès terminal distant encore à configurer.


> Déploiement du 01/10/2026 effectué : maquette publique sous `/maquette/` et
> graphes des pages de tirage en ligne. Worker
> `18285622-994a-42cc-9e0f-937b28c67f7a`, assets du commit `deedfc645`.
> Contrôles distants réussis. Le push Git a échoué sur l'accès au trousseau ;
> voir `DEPLOYMENTS.md`. Les statuts de déploiement historiques ci-dessous
> sont remplacés par cette entrée.

> Sujet éditorial à préparer : `research/sujet-editorial-hpc-combinatoire.md`,
> petit article technique sur revolving-door, bitplanes et popcount. Angle
> proposé : « Trente grilles dans quatre mots ». Brief seulement, non publié.

> Capital HPC retrouvé et documenté le 01/10/2026 : lire
> `../loto-keno-lab/docs/CAPITALISATION-HPC-ATLAS.md` avant toute nouvelle
> optimisation Atlas. B3 combine Algorithm R/revolving-door, Gray et bitplanes
> pour les 30 scores ; le worker ultérieur ajoute intervalles colex et reprise.
> Les 8,7 G combinaisons/s sont un benchmark historique borné de matching,
> pas un débit des lois de features ni un contrat multi-tailles. Les adaptations
> sont inscrites dans `TECHNICAL-DEBT.md`.

> Décision Atlas du 01/10/2026 : `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`
> définit un contrat de géométrie commun et des cohortes séparées par jeu,
> règle, format, taille et budget. Les 6 et 30 grilles sont les tailles déjà
> montrées, pas la limite du catalogue. L'Atlas v0.1 doit qualifier quelques
> références Loto et rendre les trois jeux lisibles sous un contrat commun ;
> Keno v1 reste à 10 numéros par grille en 16/56. Le Loto affiché est encore
> composé de cinq démonstrations à 6 grilles, sans évaluation exacte publiée.
> Aucun calcul massif ni changement de l'Atlas en ligne n'a été lancé. Les tâches
> d'implémentation sont dans `docs/TECHNICAL-DEBT.md`. Les garanties
> conditionnelles sont un axe de recherche hors ligne : un premier certificat
> `3 if 4 of 10` Loto prouve un minimum de 7 grilles, avec contrôle exhaustif
> des 210 scénarios. Voir `docs/research/garanties-conditionnelles-portefeuilles.md`
> et `docs/research/conditional-wheel-10-5-4-3.json`. Il ne couvre ni Chance,
> ni rang, ni rentabilité. Aucun certificat n'est encore publié sur le site.
> Demandes personnalisées, réponse différée et vente de compute restent hors
> du chemin de lancement.

> Mise à jour du 30/09/2026 : la collecte des trois jeux enchaîne maintenant avec
> les calculs locaux. `bash tools/refresh_draws.sh --check` inspecte sans réseau ;
> `bash tools/refresh_draws.sh` importe depuis `../aleaquant-data`, calcule les faits
> et régénère les pages EuroMillions/Loto si nécessaire. Keno n'a que des faits
> ciblés, sans page publiée. Aucun commit ni déploiement automatique.
> Les pages EuroMillions/Loto locales ont été régénérées avec toutes leurs lois
> scalaires représentables ; `LO-20260928` affiche désormais 18 histogrammes.
> Les queues ont un minimum visuel d'un pixel, sans modification des effectifs.
> Le détail actuel et la dette active sont dans `docs/TECHNICAL-DEBT.md`, et les
> fichiers modifiés dans `docs/CHANGELOG.md`. Les sections historiques ci-dessous
> décrivent l'état antérieur de l'agent éditorial ; leurs comptes de tirages et
> indications de déploiement ne remplacent pas ces deux documents récents.
> Maquette locale : `prototypes/editorial-home/index.html`, maintenant organisée en
> quatre rubriques et cartes de contenus. Gabarit, frontières et prochain chantier
> dans `docs/SITE-EDITORIAL-ARCHITECTURE.md`. Les 9 658 pages de tirage ont été
> régénérées avec leurs mini-histogrammes et publiées le 01/10/2026.
> La maquette distante garde un snapshot ; voir `DEPLOYMENTS.md`.
> Pages Loto et sélecteur de jeu publiés le 30/09/2026 sur
> `https://aleaquant.aleaquant.workers.dev`, version Worker
> `27128adb-e8e6-4ec5-95a3-63d98370b445`. 9 687 assets actifs ; deux URL Loto
> testées en HTTP 200 et sélecteur `/tirages/` vérifié. GitHub ne déploie pas
> automatiquement à ce stade.
> L'ajout de Keno impose un rendu à la demande ; décision et critères dans
> `docs/SCALING.md`. Le sélecteur EuroMillions/Loto est livré.
> Le calendrier d'accueil est explicitement EuroMillions ; l'archive Loto filtre par
> date sans fusionner les doubles séances. Worker actuel après cette mise à jour :
> `bcea5001-4cdc-46a9-8e46-fe79935b6d78` (9 688 assets).
> Keno : 17 lois exactes sur 20 ; génération ciblée de faits testée, aucune page
> Keno publiée. Le fait `F.draw.probability` désigne le tirage exact, jamais le gain
> d'une grille jouée. Prototype de groupes mensuels sous `prototypes/keno-on-demand/`.
> Un profil du batch et un parcours de validation humaine **court** sont désormais
> dans `../aleaquant-editorial-agents/configs/draw-publication.json` et
> `aleaquant/graph/draw_publication.py`. Le batch web garde ses défauts et reste
> à régler ; ce nouveau graphe n'importe ni ne publie automatiquement.
> Un rapport de tirage approuvé se rattache par `draw_id` à sa page canonique :
> `EM-2011053` correspond au **6 septembre 2011**, pas au 5. L'import du site
> vérifie l'empreinte des faits et actualise seulement cette page. Les autres
> tirages restent sans récit jusqu'à approbation ; le batch doit constituer ce fonds.
> Piste scientifique en dette : Coronel-Brizio et al. (2008,
> https://arxiv.org/abs/0806.4595) donnent la covariance théorique des positions
> ordonnées d'un tirage k/N. Ce n'est pas une autocovariance temporelle. Étudier son
> lien avec l'étendue et un audit historique par régime avant d'en faire un indicateur
> ou un article ; tâche détaillée dans `docs/TECHNICAL-DEBT.md`.
> Mise à jour : le calcul théorique et l'identité avec l'étendue sont vérifiés ;
> sept matrices historiques exploratoires sont enregistrées par jeu/règle dans
> `docs/research/order-position-history-2026-09-30.json`. Aucun test d'audit ni
> article n'en découle encore. La base source locale atteint le 30/09/2026 pour
> Keno ; ce rapport exploratoire antérieur n'a pas encore été régénéré.

Écrit le 30/09/2026 au matin, après une session de nuit intense sur l'agent éditorial.
**À lire en entier avant de toucher au code si vous reprenez le projet sans son
historique de conversation.** Les notes détaillées de la nuit sont dans
`docs/agent-editorial-v2-notes.md` ; ce document-ci donne l'état, les invariants et la
suite.

---

## 1. Ce que le projet doit faire

AleaQuant est un site français de vulgarisation statistique sur les jeux de tirage
(EuroMillions d'abord). Sa promesse : **expliquer le hasard avec rigueur, sans jamais
prédire ni promettre un gain.** Il publie, par tirage, une analyse de la *forme* du
tirage (somme, étendue, écarts, répartition par dizaines, historique des sous-ensembles)
appuyée sur des lois de probabilité calculées par énumération exhaustive — pas
d'échantillonnage, pas d'estimation.

Contraintes éditoriales non négociables, déjà inscrites dans le code :
- Aucune prédiction, aucune promesse de gain ; l'espérance d'une mise est négative.
- Chaque nombre publié doit venir d'un fait calculé, jamais du modèle de langage.
- Rien ne se publie sans approbation humaine explicite.
- Un tirage ordinaire est une observation valide : il ne faut pas lui fabriquer un angle
  remarquable (voir §5, c'est LE piège du projet).

---

## 2. Où ça tourne

| Quoi | Où |
|---|---|
| Dépôt | `~/aleaquant/aleaquant-web` sur le Mac de Christophe, `github.com/christophecr-bit/aleaquant` |
| Site en ligne | `https://aleaquant.aleaquant.workers.dev` (Cloudflare Worker, assets statiques) |
| Déploiement | `npx wrangler deploy` depuis le poste. **Aucun CI** : GitHub ne déploie rien. |
| Laboratoire source | `../loto-keno-lab-generic` — **lu en lecture seule** par l'engine |
| Historique | `../loto-keno-lab-generic/data/history/euromillions.sqlite3` |
| Clé OpenAI | `../aleaquant-editorial-agents/.env`, variable `OPENAI_API_KEY` |
| Modèle utilisé | `gpt-5.4-mini`, `reasoning.effort = "low"` |

Il existe un **second dépôt**, `../aleaquant-editorial-agents` : un pipeline LangGraph à
7 agents (Scout→Gate→Planner→Writer→Editor→Fact-Checker→Final-Reviewer). Son POC
traite aujourd'hui des sujets structurés ; l'extension éditoriale pourra couvrir
des articles de fond et certains rapports de tirage sélectionnés. Il ne remplace
pas le batch du dépôt web qui prépare le fonds d'articles.

---

## 3. Chaîne de données

```
labo (sqlite, patterns.py, lecture seule)
   └─ engine/exact_laws.py      → dist/data/exact_laws.json   (lois exactes, règle courante)
   └─ engine/build_data.py      → dist/data/facts/EM-*.json    (1984 fichiers, ~26 mesures + faits historiques)
                                  dist/data/draws.json, manifest.json
   └─ engine/rarity_profiles.py → dist/data/rarity_profiles.json (profil de rareté par mesure)
   └─ engine/build_pages.py     → dist/tirages/euromillions/<date>/index.html (1984 pages)
                                  dist/sitemap.xml, dist/rss.xml
   agent/*.py  → runs*/<draw_id>/draft.json  → (approbation humaine) → dist/articles.json
   dist/app.js → affiche le journal depuis articles.json
```

**`dist/` est committé dans git** : les pages sont pré-générées. Régénérer les faits
sans relancer `build_pages.py` laisse des pages fausses en ligne — piège rencontré cette
nuit.

Commande de régénération complète :
```bash
python3 engine/build_data.py --facts 2000   # 1984 fichiers, ~10 s ; défaut : 12 seulement !
python3 engine/rarity_profiles.py
python3 engine/build_pages.py
```

---

## 4. Les trois modes de rédaction (et lequel utiliser)

| Mode | Script | Statut |
|---|---|---|
| **template** déterministe | `agent/draw_report.py draft` | Fonctionne, sans LLM. Base de référence. |
| **reformulation** | `agent/llm_rewrite_test.py`, `llm_rewrite_batch.py`, `llm_batch_submit.py`, `llm_batch_collect.py` | Fonctionne (110 brouillons, batch validé) mais **abandonné** : le LLM ne voit que 7 claims déjà choisies, le résultat est cosmétique et identique d'un article à l'autre. |
| **compose** ← **le bon** | `agent/compose_draw_report.py` | Le LLM reçoit les ~26 faits annotés et compose. C'est ce mode qui a produit le premier article publié. |

Mise à jour du 30/09 : le mode compose a désormais son couple
`compose_batch_submit.py` / `compose_batch_collect.py`. L'ancien couple
`llm_batch_*` reste lié à la reformulation abandonnée. Le nouveau batch est
encore en cours de réglage avant traitement du fonds d'articles.

### Pipeline du mode compose

1. `evidence_block()` — les ~26 faits, chacun avec sa valeur, sa classe, sa queue, son
   libellé de rareté **en français**, son nom officiel et sa définition (tirés de
   `dist/metrics.json`), et surtout son statut : `AU-DESSUS de sa référence` /
   `dans sa normale — PAS notable` / `rareté NON INFORMATIVE`.
2. `family_note()` — déclare les familles emboîtées (`decade_counts` raffine
   `max_same_decade` et `occupied_decades` ; `sorted_gaps` raffine span/mean_gap/
   min_gap/max_gap) pour qu'une mesure fine plus rare qu'une mesure agrégée ne passe pas
   pour une contradiction.
3. `redundancy_note()` — déclare les mesures mathématiquement identiques
   (`span` et `mean_gap` : même classe, mean_gap = span/4).
4. Appel 1 : composition (4-6 paragraphes).
5. Appel 2 : relecture de langue uniquement, **rejetée automatiquement** si elle modifie
   un nombre ou un mot de rareté.
6. `strip_markdown()` — retire gras/titres/puces (voir invariant §6).
7. Les cinq gardes (§5), puis, si l'un échoue, une **passe de réparation** (appel 3) qui
   renvoie au modèle sa violation exacte ; acceptée seulement si tous les gardes passent
   ensuite et qu'aucun nombre nouveau n'est apparu. `--no-repair` pour désactiver.
8. `METHODO_NOTE` — note de méthode ajoutée de façon déterministe, pas rédigée par le
   modèle. Elle présente l'indépendance des tirages comme une **hypothèse du mécanisme**,
   pas comme un résultat démontré.
9. `--write` → `runs-llm-compose/<draw_id>/draft.json` au schéma `aleaquant-article-v1`.

Coûts mesurés : ~0,009 à 0,014 $ par article en direct (3 appels au pire), moitié moins
en Batch API. Reformulation : ~0,0022 $. Les 200 pages visées tiennent largement sous
3 $.

---

## 5. Les cinq gardes — et ce qu'ils ne garantissent pas

Tous déterministes, dans `agent/compose_draw_report.py` :

1. **numérique** (`guard_full_text`) — tout nombre du texte doit venir des faits.
   Tolérance sur les pourcentages arrondis ; les bornes de dizaines (1-10, 11-20…) ne
   sont acceptées que dans un contexte de plage explicite, jamais en liste blanche.
2. **lexical** (`guard_interpretive_words`) — un mot de rareté (rare, très rare,
   notable, exceptionnel, peu courant, inhabituel ; négations ignorées) n'est autorisé
   que si une mesure **dépasse sa propre référence**.
3. **jargon** (`guard_enum_leak`) — aucun nom de code (`COMMON`, `VERY_RARE`…) dans la
   prose française.
4. **effectifs** (`guard_class_citations`) — chaque « classe de N sur M » et chaque
   « queue de X % » cités doivent exister dans les faits.
5. **mise en forme** (`guard_markdown`) — aucun marqueur markdown résiduel.

Plus deux avertissements non bloquants : qualificatif global appliqué au tirage entier
(« configuration serrée »), et dernier paragraphe purement récapitulatif.

### Ce que les gardes NE font PAS — à retenir absolument

- **Ils vérifient la fidélité du texte aux faits, jamais l'exactitude des faits.** Un
  bug de l'engine passe tous les gardes. C'est exactement ce qui est arrivé : 940
  tirages sur 1984 annonçaient une probabilité fausse, le texte la recopiait
  fidèlement, les cinq gardes disaient OK. L'exactitude des faits ne peut venir que de
  tests sur `engine/` (`tests/test_rules.py`).
- **Ils n'apparient pas encore un mot au fait précis qu'il décrit.** Le garde lexical
  vérifie qu'*au moins une* mesure justifie le niveau employé, pas que la phrase
  attribue le bon niveau à la bonne mesure. `paragraph_evidence()` est le début de cet
  appariement (voir §7, tâche 3).

### Le concept central : niveau de référence

`dist/data/rarity_profiles.json` (produit par `engine/rarity_profiles.py`) donne, pour
chacune des 26 mesures, la distribution de ses niveaux de rareté sur les 1984 tirages et
son **niveau de référence** (le plus fréquent). **Une mesure n'est notable que si son
niveau dépasse sa référence.**

Sans cette notion, le garde lexical était structurellement incapable de se déclencher :
`main.sorted_gaps` est `VERY_RARE` pour **tout tirage possible** (1 725 profils d'écarts
distincts, plus grande classe observée 888 combinaisons, seuil à 2 119), donc le maximum
de rareté valait toujours `VERY_RARE` et aucune inflation ne pouvait être signalée.

Chiffres à connaître :
- **6 mesures sur 26 ont une rareté constante** : `sorted_gaps` (toujours très rare),
  `is_arithmetic_progression`, `stars.consecutive`, `stars.odd_count`, `stars.low_count`
  (toujours courantes), `stars.sum` (toujours peu courante). **Jamais de badge dessus.**
- **5 autres ne sont jamais courantes** : `sum`, `span`, `mean_gap`, `max_gap`,
  `decade_counts`. « Peu courante » y est la normale, pas une information.
- **486 tirages sur 1984 (24,5 %) n'ont AUCUNE mesure au-dessus de sa référence.** Pour
  eux, l'article ne doit employer aucun mot de rareté et dire simplement que la forme est
  ordinaire. C'est le piège des comparaisons multiples : avec 26 mesures, on trouvera
  toujours « quelque chose de remarquable » si on ne s'en méfie pas.

---

## 6. Invariants à ne pas casser

1. **`dist/app.js` rend le corps des articles avec `textContent`, jamais `innerHTML`.**
   Choix de sécurité assumé : le texte vient d'un LLM. Conséquence : pas de markdown, pas
   de HTML dans le corps. Pour de la mise en forme ou des puces, il faut un **champ
   structuré** calculé côté Python et rendu élément par élément (voir §7, tâche 2).
2. **Les empreintes protègent les brouillons.** `decide()` refuse un `draft.json` modifié
   après génération, `import_article.validate()` refuse un article non approuvé ou dont
   l'empreinte ne correspond plus, et `app.js` n'affiche que les articles dont
   `human_decision.draft_sha256 == draft_sha256`. **Ne jamais corriger un article à la
   main** : régénérer.
3. **La probabilité de la combinaison complète dépend de la règle du tirage**, pas de la
   règle courante. `rule_star_total()` / `rule_domains()` dans `engine/common.py` la
   dérivent de l'identifiant de règle, et **lèvent une exception** sur une règle inconnue
   plutôt que de retomber silencieusement sur la règle courante — c'est ce silence qui
   avait laissé passer le bug.

   | Règle | Tirages | Période | Probabilité |
   |---|---|---|---|
   | `euromillions-50-9-v1` | 378 | 13/02/2004 → 06/05/2011 | 1 sur 76 275 360 |
   | `euromillions-50-11-v1` | 562 | 10/05/2011 → 23/09/2016 | 1 sur 116 531 800 |
   | `euromillions-50-12-v1` | 1044 | 27/09/2016 → 25/09/2026 | 1 sur 139 838 160 |

   Les métriques des cinq numéros gardent C(50,5) = 2 118 760, inchangé par les règles
   d'étoiles. Les lois d'étoiles sont déjà écartées pour les anciennes règles
   (`facts.py`, comparaison à `CURRENT_RULE`).
4. **Le laboratoire est en lecture seule.** Ne pas modifier
   `../loto-keno-lab-generic/...` ; adapter dans `engine/` (c'est ainsi que la signature
   a été traduite en français côté `facts.py`, le code brut restant dans
   `value.signature`).
5. **`engine/build_data.py` ne régénère que 12 tirages par défaut** (`--facts 12`).
   Utiliser `--facts 2000` pour tout l'historique.
6. **Python** : le Terminal de Christophe est en 3.9 (Command Line Tools). Ne pas
   utiliser de syntaxe postérieure.
7. **Réseau** : dans l'environnement de l'assistant, `api.openai.com` et l'API Cloudflare
   sont bloqués, et `wrangler` n'y est pas authentifié. Tout appel API OpenAI et tout
   `wrangler deploy` doivent être lancés par Christophe dans son propre Terminal.

---

## 7. État au 30/09/2026, 8 h 40

### Fait et vérifié

- **Bug de probabilité corrigé** : 940 fichiers de faits et 1984 pages régénérés,
  vérifiés en ligne (la page du 06/09/2011 affiche bien 1 sur 116 531 800).
- **Profil de rareté** calculé et branché sur l'agent ; garde lexical réparé et prouvé
  capable de bloquer (il a refusé un article sur EM-26077, tirage ordinaire, où le
  modèle avait fabriqué de la notabilité).
- **Cinq gardes + relecture contrôlée + réparation automatique** en place.
- **Libellés lisibles** : règle nommée dans la probabilité, signature traduite en
  français, noms et définitions officiels des métriques transmis au modèle.
- **Chaîne de publication complète et éprouvée** : `--write` → `show` → `approve` →
  `wrangler deploy`. **Premier article publié** : `tirage-EM-2011053`.
- **26 tests** (`tests/test_rules.py`, `test_guards.py`, `test_import.py`), tous verts.
- Pédagogie du site : section Atlas et notion de paire expliquées en clair.

### En attente à l'instantané du 30/09 — historique, pas la liste active

1. **`git push`** — 5 commits locaux non poussés (`origin/main` est à `0dc23ba`,
   local à `aaba02c`).
2. **`dist/articles.json` non committé** — l'article régénéré sans markdown est sur le
   disque mais pas dans git.
3. **`npx wrangler deploy`** — **la version en ligne de l'article contient encore les
   `**`** : il a été régénéré proprement et approuvé, mais pas redéployé.
4. Un batch OpenAI de 10 items a été validé end-to-end en mode reformulation
   (`batch_6abc41d36c28819082ad64bbb03fd9a5`, terminé, 0,0103 $).

### Ancienne todolist du matin — archive

Cette liste décrivait un état antérieur et mélangeait défauts, fonctionnalités et
pistes d'architecture. Elle n'est plus une liste de tâches active. Consulter
`docs/ROADMAP.md`, `docs/TECHNICAL-DEBT.md` et `docs/TASKS.md` pour l'état courant ;
les notes historiques de l'agent restent dans `docs/agent-editorial-v2-notes.md`.

---

## 8. Leçons de méthode (chèrement acquises)

- **Valider un garde sur l'historique réel, jamais sur des cas synthétiques.** Le garde
  lexical a été testé sur des faits fabriqués à la main et paraissait fonctionner ; sur
  données réelles il ne pouvait pas se déclencher. Une requête de dix secondes sur les
  1 984 fichiers l'aurait montré immédiatement.
- **Un « OK » de garde ne prouve rien tant qu'on ne l'a pas vu échouer** sur un cas où il
  devrait échouer.
- **Les gardes contrôlent la fidélité, pas la vérité.** Les deux vraies erreurs de la
  session (probabilité par règle, garde inopérant) ont été trouvées l'une par une
  relecture humaine avec vérification réglementaire externe, l'autre par un audit à
  l'échelle — aucune par les gardes.
- **Corriger à la source plutôt que par consigne.** Un libellé de fait faux ou opaque se
  corrige dans `engine/` : ça profite aussi aux pages du site, et une consigne de prompt
  se contourne alors qu'un libellé source ne se contourne pas.
- **Avec 26 mesures par tirage, le remarquable est garanti par construction.** Tout le
  dispositif de référence existe pour résister à cette tentation.

---

## 9. Expérience éditoriale A/B/C du 30/09/2026

Un prototype optionnel, versionné dans `agent/prompts/editorial_angle.md`, propose
trois titres A/B/C, chacun lié à un à trois faits. Le choix humain est enregistré
pour un **essai direct** ; le batch `compose_batch_*`, en cours de réglage pour
constituer le fonds d'articles, ne charge pas ces angles et garde son prompt de base.
`agent/prompts/editorial_polish.md` crée une copie relue avec nouveau SHA ; ses
contrôles refusent les changements de nombres, de rareté et de faits cités.
Le format « décade 2, 3, 4 » est testé dans ce prototype, pas imposé au batch.

Essai local sur `EM-26078` : A a été choisi et révisé en « Une grille qui traverse
quatre dizaines », à partir de `F.main.occupied_decades = 4`. Le brouillon et sa
relecture restent en attente d'approbation humaine dans `runs-llm-compose/EM-26078/` ;
aucune publication n'a été lancée. Les titres B/C sont conservés dans
`runs-angles/EM-26078/` pour comparaison.

Le **comité LangGraph canonique** est dans `../aleaquant-editorial-agents` : son graphe
POC fonctionne, mais cette sélection A/B/C, la relecture de ton, la file matinale
et le retour humain avec remarque n'y sont pas encore branchés. La feuille de
route autoritative est `docs/roadmap-editorial-agentique.md` dans ce dépôt.
Évaluer le prototype sur plusieurs tirages avant tout portage.


## État du calcul exact Keno 16/56 — 1er octobre 2026

Le scan Metal du M4 Pro est terminé : 4 165 fragments contigus couvrent C(56,16),
les histogrammes `arithmetic_triples` et `longest_arithmetic_progression` totalisent
chacun 41 648 951 840 265. Dans le working tree local, AleaQuant charge ces lois,
reconstruit le JSON 16/56 à 20 métriques, les 31 faits Keno présents et leur profil de
rareté. Les tests ciblés lois/récurrences et faits génériques passent (18 tests).
Aucun déploiement n'a eu lieu. La comparaison Metal/Rayon exhaustive, le profil sur
l'ensemble de l'historique 16/56 et la qualification des pages Keno restent à faire.
Le régime historique 20/70 demeure séparé et incomplet pour ces trois lois.

## Reprise — traçabilité, 2 octobre 2026

Voir ARTICLE-TRACEABILITY.md et l'entrée CHANGELOG correspondante. Les témoins
originaux sont préservés ; nouveau draft dans runs-traceability/EM-26078-v2/.
128 tests web (+28 sous-tests), 119 agents passent. Aucune publication. Relire le
nouveau témoin et traiter les dates/URL manquantes avant de généraliser le rattrapage.
