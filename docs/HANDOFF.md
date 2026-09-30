# AleaQuant — document de reprise (handoff)

> Mise à jour du 30/09/2026 : les pages Loto et les premières lois Keno ont avancé.
> Le détail actuel et la dette active sont dans `docs/TECHNICAL-DEBT.md`, et les
> fichiers modifiés dans `docs/CHANGELOG.md`. Les sections historiques ci-dessous
> décrivent l'état antérieur de l'agent éditorial ; leurs comptes de tirages et
> indications de déploiement ne remplacent pas ces deux documents récents.
> Maquette locale : `prototypes/editorial-home/index.html`, maintenant organisée en
> quatre rubriques et cartes de contenus. Gabarit, frontières et prochain chantier
> dans `docs/SITE-EDITORIAL-ARCHITECTURE.md`. Les 9 657 pages de tirage ont été
> régénérées **localement** avec leurs mini-histogrammes ; aucun déploiement de ce
> correctif n'a été effectué. Le fil de l'accueil reste un snapshot.
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
> article n'en découle encore. La source Keno locale s'arrête au 17/09/2026.

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
| Dépôt | `~/aleaquant-web` sur le Mac de Christophe, `github.com/christophecr-bit/aleaquant` |
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

### En attente d'une action de Christophe

1. **`git push`** — 5 commits locaux non poussés (`origin/main` est à `0dc23ba`,
   local à `aaba02c`).
2. **`dist/articles.json` non committé** — l'article régénéré sans markdown est sur le
   disque mais pas dans git.
3. **`npx wrangler deploy`** — **la version en ligne de l'article contient encore les
   `**`** : il a été régénéré proprement et approuvé, mais pas redéployé.
4. Un batch OpenAI de 10 items a été validé end-to-end en mode reformulation
   (`batch_6abc41d36c28819082ad64bbb03fd9a5`, terminé, 0,0103 $).

### Ancienne todolist du matin (état figé, remplacé par `docs/TECHNICAL-DEBT.md`)

1. **Portage réalisé depuis** dans `compose_batch_submit.py` /
   `compose_batch_collect.py`. Le batch compose reste à régler avant constitution
   du fonds ; ne pas relancer l'ancienne reformulation `llm_batch_*`.
2. **Puces de rareté dans l'article** (demande du 30/09 matin). Critère d'affichage :
   uniquement une mesure au-dessus de sa référence (`notable_level()`). Implémentation :
   champ `draft.badges` calculé côté Python, rendu par `app.js` avec les classes CSS des
   badges existants, croisable avec `claims[].evidence_ids` pour le placement par
   paragraphe. **Jamais de markdown ni de `innerHTML`.** Détail dans
   `docs/agent-editorial-v2-notes.md`.
3. **Appariement mot ↔ fait** : faire taguer par le modèle chaque affirmation de rareté
   avec son `fact_id`, et vérifier le niveau de CE fait — au lieu du « au moins une
   mesure quelque part » actuel. `paragraph_evidence()` en est la première brique.
4. **Radar de signature** (piste B) : mêmes axes que les puces, rayon = niveau ordinal.
   Après stabilisation des puces. Risque à traiter : ne pas laisser croire qu'une grande
   aire signifie quoi que ce soit sur un tirage futur.
5. **Petit défaut connu** : `paragraph_evidence()` ignore les faits sans `metric`, donc
   le paragraphe qui cite la probabilité de la combinaison complète
   (`F.grid.probability`) n'a aucun fait attribué. Inclure les faits non métriques par
   leurs nombres distinctifs.
6. **Encadré méthodologique commun** : `METHODO_NOTE` est pour l'instant collée à la fin
  de chaque corps d'article. Mieux vaudrait un encadré rendu une fois par la page.
7. **Accueil éditorial et Atlas** : poursuivre la maquette locale `prototypes/editorial-home/`
   (cartes, fil des derniers tirages, image AleaQuant originale), puis préparer un premier
   Atlas de portefeuilles. Avant l'outil, publier des articles de fond qui présentent les
   familles de portefeuilles et expliquent leur géométrie (couverture, recouvrement,
   dispersion) sans promesse de gain. Le fil de tirages utilise encore un snapshot ; son
   raccordement aux données locales actualisées par jeu reste à concevoir.

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
