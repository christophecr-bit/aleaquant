# Les gardes du pipeline éditorial — ce qu'ils vérifient, et l'échec qui les a fait naître

`agent/guards.py` · tests dans `tests/test_guards.py` · linter dans `tools/lint_language.py`

Ce document existe parce qu'un garde sans son histoire finit par être assoupli par
quelqu'un qui le croit trop strict. **Chaque entrée ci-dessous nomme l'échec réel qui a
motivé le contrôle.** Les tests encodent ces échecs : si un test tombe, relire l'entrée
correspondante avant de toucher au code.

## L'architecture, en une phrase

**Les faits sont calculés et annotés de façon déterministe ; un LLM les relie en prose ;
des contrôles déterministes refusent ou font corriger ce qu'il a écrit.** Le LLM ne
produit jamais un nombre, un niveau de rareté ou une puce — seulement du texte qui doit
survivre aux contrôles.

Décision du 30/09/2026 : c'est bien cette forme qui est retenue pour les rapports de
tirage, et non des trames de texte déterministes comme le prévoyait `ARCHITECTURE.md`
§8.3 à l'origine. Raison : les trames produisaient des articles interchangeables, alors
que les gardes déterministes donnent au LLM une liberté de rédaction sans lui laisser la
main sur les chiffres. Le coût mesuré reste d'environ un centime par article.

---

## Couche 1 — préparation des faits

### `evidence_block()` — annoter, pas seulement transmettre

Chaque fait est transmis avec sa valeur, sa classe, sa queue, son libellé de rareté **en
français**, son nom officiel et sa définition (issus de `dist/metrics.json`), et surtout
son statut : *au-dessus de sa référence* / *dans sa normale* / *rareté non informative*.

**Échec d'origine** : une première version filtrait les faits sans champ `metric`, ce qui
excluait `F.history.exact_main` et `F.signature`. L'article affirmait alors qu'on ne
pouvait rien dire de l'historique, alors que le fait était disponible mais jamais montré
au modèle. Un second échec, plus tard : le libellé de rareté était transmis comme nom de
code anglais (`VERY_RARE`), que le modèle recopiait tel quel dans la prose française.

### `family_note()` — les familles emboîtées

`main.decade_counts` décrit la configuration exacte des dizaines ; `max_same_decade` et
`occupied_decades` n'en résument qu'un aspect. Idem pour `sorted_gaps` face à
`span`/`mean_gap`/`min_gap`/`max_gap`. La mesure fine est plus spécifique, donc
normalement plus rare.

**Échec d'origine** : un article annonçait « 4 numéros dans une même dizaine : peu
courant » et « répartition 0-0-0-1-4 : très rare » dans le même paragraphe, ce qui
ressemblait à une contradiction. Ce n'en est pas une, mais le texte devait le dire.

### `redundancy_note()` — les métriques qui n'en sont qu'une

`mean_gap = span / 4` exactement (cinq numéros, quatre écarts) : mêmes classes, mêmes
probabilités. Les citer comme deux constats distincts double-compte la preuve.

**Échec d'origine** : un article présentait l'étendue et l'écart moyen comme deux
indices concordants de resserrement. C'était deux fois le même indice.

---

## Couche 2 — les six gardes

### 1. `guard_full_text()` — aucun nombre inventé

Tout nombre du texte doit venir des faits. Tolérance sur les pourcentages arrondis. Les
bornes de tranches de dizaines (1-10, 11-20…) sont acceptées **uniquement dans un
contexte de plage explicite**, jamais par liste blanche globale — sinon un « 20 » isolé
ailleurs cesserait d'être contrôlé.

**Échec d'origine** : faux positif sur 20/31/40/41, qui étaient des conventions
d'affichage et non des mesures. La précision du correctif (contexte, pas liste blanche)
vient de Christophe.

### 2. `guard_interpretive_words()` — un mot de rareté doit être mérité

Un mot de rareté (*rare*, *très rare*, *notable*, *exceptionnel*, *peu courant*,
*inhabituel* ; négations ignorées) n'est autorisé que si une mesure **dépasse la
référence de sa propre distribution** (`dist/data/rarity_profiles.json`).

**Échec d'origine — le plus instructif de tous.** La première version comparait le mot au
maximum de rareté de l'ensemble des faits. Or `main.sorted_gaps` est `VERY_RARE` pour
**tout tirage possible** (1 725 profils d'écarts distincts, plus grande classe observée
888 combinaisons, seuil à 2 119) : ce maximum valait donc toujours `VERY_RARE`, et le
garde ne pouvait **jamais** se déclencher. Il a affiché « OK » sur tous les articles d'une
soirée entière sans rien vérifier. Découvert non pas en lisant un article, mais en
comptant sur les 1 984 fichiers de faits : 100 % des tirages ont au moins une mesure
« très rare ».

**Leçon générale, qui vaut pour tout garde futur** : un garde qu'on n'a jamais vu échouer
sur données réelles n'est pas validé. Le tester sur l'historique complet, jamais
seulement sur des cas fabriqués pour l'occasion — ce sont des faits synthétiques,
plafonnés à `RARE`, qui donnaient l'illusion que celui-ci fonctionnait.

**Conséquence éditoriale** : 486 tirages sur 1 984 (24,5 %) n'ont aucune mesure au-dessus
de sa référence. Un quart des tirages n'a objectivement rien de remarquable, et l'article
doit pouvoir le dire. Avec 26 mesures par tirage, le remarquable est garanti par
construction si l'on ne s'en méfie pas : c'est le problème des comparaisons multiples.

### 3. `guard_enum_leak()` — pas de nom de code dans la prose

Aucun `COMMON`, `UNCOMMON`, `RARE`, `VERY_RARE` dans le texte français.

**Échec d'origine** : le modèle écrivait « classée VERY_RARE », « ce qui est dans la zone
COMMON ». Corrigé à la source (traduction en amont via `RARITY_FR`), le garde reste comme
filet.

### 4. `guard_class_citations()` — les effectifs cités doivent exister

Chaque « classe de N sur M » et chaque « queue de X % » sont confrontés aux faits.

**Échec d'origine** : aucun — au contraire. Les six effectifs d'un article avaient été
vérifiés à la main et étaient exacts ; ce garde existe pour que ce ne soit pas à refaire
sur 2 000 articles. Piège technique rencontré à l'écriture : un motif paresseux tronquait
« 2 118 760 » au premier « 2 ».

### 5. `guard_markdown()` — le site rend du texte, pas du balisage

`dist/app.js` affiche le corps avec `textContent`, jamais `innerHTML` — choix de sécurité
assumé puisque le texte vient d'un LLM.

**Échec d'origine** : les `**Somme**` du modèle se sont affichés littéralement sur le
site publié. Corrigé par `strip_markdown()` appliqué avant tout contrôle, plutôt que par
une consigne que le modèle peut ignorer.

**Corollaire à retenir** : toute mise en forme future (intertitres, listes, puces) doit
passer par un champ **structuré** calculé côté Python et rendu élément par élément —
jamais par du balisage dans le corps. C'est ainsi que `draft.badges` fonctionne.

### 6. `lint_language()` — la ligne éditoriale comme test

Douze règles refusant toute formulation prédictive ou promesse de gain (*va sortir*,
*chances augmentées*, *meilleure grille*, *numéros chauds*, *en retard donc*…), chacune
avec le message disant quoi écrire à la place. Analyse **par phrase**, avec exception
évaluée sur la phrase entière : c'est le contexte qui distingue « aucune mesure ne prédit
le prochain tirage » de « à jouer au prochain tirage ».

Branché en sortie d'agent **et** dans `scripts/import_article.validate()` : un vocabulaire
interdit refuse l'import dans le site, il n'avertit pas.

Son corpus (`INTERDITES`, `LEGITIMES` dans `tools/lint_language.py`) est sa spécification
exécutable. Trois défauts trouvés à l'écriture, tous par ce corpus : « meilleures chances »
manqué parce que l'adjectif précédait le nom, et deux formulations légitimes refusées
parce qu'un *lookahead* ne voit pas une négation qui précède.

### Avertissements non bloquants

- `warn_global_qualifiers()` — un adjectif géométrique appliqué au tirage entier
  (« configuration serrée ») alors que chaque mesure a sa propre classe. C'est un choix
  éditorial, pas une erreur factuelle : signalé, pas bloqué.
- `warn_redundant_closing()` — dernier paragraphe dont tous les chiffres ont déjà été
  cités : récapitulatif sans élément neuf.

---

## Couche 3 — sortie

### `paragraph_evidence()` — appariement paragraphe / fait

Deux voies seulement : l'effectif de classe du fait apparaît (nombre distinctif), ou sa
valeur **et** le nom de la mesure apparaissent. Les faits sans champ `metric` sont
appariés par un nombre d'au moins quatre chiffres ou une expression caractéristique.

**Échec d'origine** : une première version attribuait vingt faits à un même paragraphe,
parce qu'une valeur comme « 2 » ou « 4 » se retrouve dans presque toutes les mesures. Une
attribution qui désigne tout ne désigne rien. Le domaine (2 118 760) est exclu pour la
même raison : commun à tous les faits.

### `notable_badges()` — les puces de rareté

Une puce **uniquement** pour une mesure au-dessus de sa propre référence, avec son nom
officiel, sa valeur, son libellé français et la part des tirages qui dépassent ce niveau.
Doublons redondants écartés, plafond à cinq, calcul entièrement déterministe.

**Pourquoi ce critère** : un badge n'informe que si la mesure peut aussi *ne pas* être
rare. Six mesures sur 26 ont une rareté constante sur tout l'historique
(`sorted_gaps` toujours très rare ; `is_arithmetic_progression`, `stars.consecutive`,
`stars.odd_count`, `stars.low_count` toujours courantes ; `stars.sum` toujours peu
courante) : jamais de puce dessus. Cinq autres ne sont jamais courantes (`sum`, `span`,
`mean_gap`, `max_gap`, `decade_counts`) : « peu courante » y est la normale.

### `repair_prompt()` — faire corriger plutôt que jeter

Quand un garde bloque, le modèle reçoit sa violation exacte et l'état réel du tirage.
Quand aucune mesure ne dépasse sa référence, le prompt le dit explicitement et demande de
décrire une forme ordinaire au lieu de chercher un angle. La réparation n'est acceptée que
si **tous** les gardes passent ensuite **et** qu'aucun nombre nouveau n'est apparu.

---

## Ce que les gardes ne garantissent pas

**Ils vérifient la fidélité du texte aux faits, jamais l'exactitude des faits.** Un bug du
moteur passe tous les gardes sans exception.

C'est arrivé : `F.grid.probability` appliquait la règle courante à douze étoiles à tous les
tirages, donc 940 tirages sur 1 984 annonçaient une probabilité fausse. Le texte la
recopiait fidèlement, les cinq gardes disaient « OK », et l'erreur n'a été trouvée que
parce que Christophe a vérifié le règlement publié au Journal officiel. L'exactitude des
faits ne peut venir que de tests sur `engine/` — voir `tests/test_rules.py`.

Ils n'apparient pas non plus encore un mot au fait **précis** qu'il décrit : le garde
lexical vérifie qu'au moins une mesure justifie le niveau employé, pas que la phrase
attribue le bon niveau à la bonne mesure. `paragraph_evidence()` est la première brique de
cet appariement ; le reste est à faire.

---

## Divergences connues avec `ARCHITECTURE.md` §6 / `TODO-V0.md` D1

À trancher, elles ne sont pas résolues :

1. §6 demande d'exclure `sorted_gaps` **et `decade_counts`** de la qualification. Ici
   `sorted_gaps` est exclu (rareté constante) mais `decade_counts` est conservé, avec sa
   référence à `RARE` : seules les 2 % de tirages qui la dépassent sont signalés.
2. §6 organise la qualification en **six axes** nommés (étalement, concentration,
   contiguïté, équilibre, régularité, position) ; ici les puces sont par métrique.
3. §6 veut l'atypicité comme plus petite queue bilatérale avec **correction de Šidák** ;
   ici c'est un niveau de référence empirique par mesure, qui traite le même problème de
   comparaisons multiples mais sans correction analytique.
4. §6 impose qu'« une étiquette sans taux de base n'est pas émise » ; ici le taux est dans
   l'infobulle de la puce, pas dans son libellé visible.
5. La déduplication est déclarée à la main (`DERIVED_EQUIVALENTS`) au lieu d'être détectée
   par signature de classes identiques, comme le demande D1.
