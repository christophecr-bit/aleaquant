# Agent éditorial — notes de session (29-30/09/2026)

Trois itérations testées dans la nuit sur `agent/llm_compose_test.py` (et son prédécesseur
claim-par-claim `agent/llm_rewrite_batch.py`), sur des tirages réels. Objectif : passer du
brouillon déterministe (`agent/draw_report.py`, mode `template`) à un article réellement
rédigé, sans rien inventer.

## Ce qui a été essayé, et pourquoi ce n'est pas suffisant tel quel

1. **Reformulation phrase à phrase** (`llm_rewrite_batch.py`) : le LLM ne voit que les
   ~7 claims déjà sélectionnées par `select()` dans `draw_report.py`. Résultat testé sur
   100 tirages réels (100/100 OK, 0 bloqué, 0,21 $) : texte fidèle mais **cosmétique**,
   même squelette d'un article à l'autre, aucune analyse nouvelle.

2. **Composition avec tous les faits, sans garde-fou éditorial** (`llm_compose_test.py`,
   v1) : le LLM reçoit les ~31 faits calculés (dont géométrie : étendue, écarts, dizaines,
   paires proches) et compose librement. Résultat : **inventaire de métriques**, pas un
   article — empile les chiffres sans hiérarchie, répète le rappel "pas de prédiction" à
   plusieurs endroits, et contient une **incohérence analytique** relevée : qualifie un
   tirage d'"étendue 38" (quasi tout le domaine 1-50) de "concentré" en ne regardant que
   les 2-3 premiers écarts sans les situer par rapport à l'ensemble.

   Bug technique trouvé en même temps : `evidence_block()` filtrait tout fait avec
   `metric is None`, excluant sans le vouloir `F.history.exact_main` ET `F.signature` —
   qui contient pourtant exactement la référence historique avec échelle demandée
   ("signature déjà observée 156 fois sur 1983 tirages antérieurs"). Corrigé.

3. **Composition avec consignes plus strictes** (v2, après correction du filtre) :
   net progrès — le texte exploite maintenant la signature historique, précise les
   tranches de dizaines, construit un vrai angle (géométrie + queues de distribution).
   Coût mesuré : 0,00645 $/article. Mais :
   - **Faux positif du garde** : les bornes de tranches (10, 20, 30, 40, 50, ou plus
     précisément 20/31/40/41 tels qu'écrits) ne sont pas dans les facts, donc rejetées —
     alors que ce sont des conventions d'affichage légitimes, pas des chiffres mesurés.
     Le garde doit les accepter explicitement (comme il le fait déjà pour {2,3,5,10} en
     dur dans `draw_report.guard()`).
   - **Confusion classe / queue** : le texte dit "quelques mesures se placent dans des
     queues basses" en mélangeant `p_class` (taille de la classe, ex. somme à 1,2 %) et
     `tail` (probabilité de queue cumulée). Ce sont deux notions diférentes ; le prompt
     doit forcer la distinction.
   - **Synthèses non ancrées** : "sans accumulation exceptionnelle sur tous les plans"
     est une conclusion du modèle non strictement dérivée des chiffres cités — à
     interdire ou à exiger justifiée fait par fait.
   - **Signature peu expliquée** : "déjà rencontrée 156 fois" sans que le lecteur sache
     ce que la signature résume (run, decade_max, decades) — nécessite une phrase de
     définition.
   - **Nuance à ajouter** : distinguer clairement "les cinq numéros principaux" de "la
     combinaison complète (numéros + étoiles)" dans toute affirmation d'historique —
     `F.history.exact_main` ne couvre que les numéros principaux, jamais la combinaison
     complète avec étoiles ; ne jamais laisser le texte suggérer le contraire.

## Le vrai manque (diagnostic validé sur les 3 essais)

Ce n'est pas une question de volume de faits donnés au modèle. C'est l'absence d'une
**couche d'analyse et de contrôle** entre les facts et la rédaction :

1. **Une question éditoriale par article**, puis sélection des seules mesures qui y
   répondent — pas un balayage de toutes les métriques disponibles.
2. **Position dans la distribution**, pas la valeur brute : dispersion, décades etc.
   affichées avec leur rang / comparaison à une référence, jamais isolées.
3. **Historique contextualisé à l'échelle** : fréquence attendue, nombre de tirages
   couverts — jamais un compteur brut sans repère (déjà en grande partie disponible via
   `F.signature`, à condition de ne pas la filtrer).
4. **Filtrer le banal, signaler le rare avec prudence** en précisant qu'on a examiné
   plusieurs métriques (limiter le biais de sélection après coup).
5. **Le rappel "pas de prédiction" en encadré méthodologique commun ** (une fois pour le
   site), pas répété à chaque paragraphe d'article.
6. **Contrôle post-génération des mots interprétatifs** ("rare", "concentré", "notable",
   "exceptionnel") : chacun doit pointer vers un fait précis et sa définition/distribution
   de référence, jamais laissé comme impression libre du modèle.
7. **Garde numérique élargi** pour accepter les bornes de catégories légitimes (tranches
   de dizaines, etc.) sans pour autant relâcher le contrôle sur les vrais chiffres mesurés.
   Précision : ne pas les ajouter à un ensemble de nombres globalement autorisés (trop permissif, ils pourraient alors justifier n'importe quelle autre affirmation) — les reconnaître uniquement dans le contexte précis d'une description de tranches (ex. motif « 1–10, 11–20, …, 41–50 »), pour continuer à signaler un 20/31/40/41 injustifié ailleurs dans le texte.

## Prochaine étape concrète proposée

Prendre 2-3 tirages de référence (un ordinaire, un avec queue de somme, un avec
signature très répétée), calculer à la main leurs mesures de dispersion/décades/
historique, et comparer à ce que le modèle peut en dire une fois les points 1-7
ci-dessus adressés — avant de relancer un lot à l'échelle.

Coûts mesurés cette nuit (gpt-5.4-mini, reasoning effort low) :
- Reformulation claim-par-claim : ~0,0022 $/article
- Composition texte libre (v1/v2) : ~0,005-0,0065 $/article
- Batch API (submit/collect scripts prêts, testés end-to-end sur 10 items, non encore
  utilisés à l'échelle) : ~50 % moins cher que ces tarifs directs.


## Round 4 — après patch du garde (bornes de dizaines en contexte)

Fix appliqué : `decade_range_numbers()` dans `llm_compose_test.py` reconnaît les bornes
(1,10,11,20,...,41,50) uniquement quand elles apparaissent dans un motif de plage explicite
("1-10, 11-20, ..."), pas en liste blanche globale — un `20` isolé ailleurs reste signalé.
Testé sur EM-26077 et EM-2011053 : garde OK sur les deux, plus de faux positif.

**Vrai progrès** : les deux articles ont une structure de lecture complète (géométrie,
forme, historique, limites). Le second (EM-2011053) distingue spontanément classe et queue
pour la somme ("c'est donc la queue de la somme qui mérite l'attention ici, pas une autre")
— exactement la confusion relevée au round précédent, résolue sans qu'on ait dû le forcer
explicitement dans le prompt cette fois. Historique bien contextualisé à l'échelle des deux
côtés ("156 fois sur 1983 tirages", "7 fois sur 412 tirages").

Restes à traiter avant de considérer la composition libre fiable à l'échelle :
- **Métriques dérivées non définies inline** : "écart moyen de 3,75" est cité sans jamais
  expliquer que c'est la moyenne des écarts entre numéros triés consécutifs — le lecteur
  doit pouvoir comprendre chaque métrique sans dictionnaire externe.
- **Ambiguïté de comptage** : "une seule paire consécutive" vs "quatre paires à distance
  d'au plus 5" — préciser si les paires consécutives (distance 1) sont incluses dans ce
  second compte ou comptées à part.
- **Jugements qualitatifs non cadrés** : "le chiffre le plus frappant", "entièrement
  compatible" — nécessitent une règle éditoriale stable (quel seuil déclenche quel
  qualificatif) plutôt que laissés à l'appréciation libre du modèle à chaque génération.
- **Le garde ne valide que les nombres, pas les définitions ni la cohérence des calculs
  dérivés** ("écart moyen" est-il vraiment la moyenne des écarts cités ?) — il faudrait une
  vérification déterministe séparée pour les métriques calculées à partir d'autres nombres
  du texte, pas seulement leur présence dans les facts.

Conclusion de Christophe : garder cette direction (composition libre + garde), en ajoutant
une validation déterministe renforcée des calculs dérivés et une règle claire d'usage pour
"rare", "queue", "frappant", "exceptionnel".

## Piste retenue : réutiliser les badges de rareté existants (30/09/2026, ~1h30)

Vérification sur EM-2011053 (somme = 222) : chaque fait métrique porte déjà un champ
`rarity` calculé (COMMON/UNCOMMON/RARE/VERY_RARE), pas seulement `p_class`/`tail`. Pour
ce tirage, `F.main.sum.rarity = VERY_RARE` (p_class ≈ 0,0067 %, tail ≈ 0,036 %) — donc
« très rare », pas « rare ». Rien à inventer : le classement existe déjà fait par fait,
sur l'échelle même des badges déjà affichés en UI (mini-histogrammes).

Décision : ce champ `rarity` devient **la règle éditoriale stable pour les mots
interprétatifs** (remplace le point 6 ci-dessus) — un article ne doit jamais qualifier
un chiffre de « rare »/« notable »/« exceptionnel » sans que ce soit littéralement la
valeur de `rarity` du fait cité, jamais une impression libre du LLM.

### Deux pistes de restitution visuelle, à mettre en todolist

**A — Puces de signature (priorité haute)**
Ligne fixe de 5-6 badges par article, toujours les mêmes métriques dans le même ordre :
Somme · Étendue · Écart moyen · Concentration en décades (max_same_decade) · Paires
proches (clusteredness_close_pairs_5) · Plus longue suite consécutive. Chaque puce =
nom + couleur du badge `rarity`, cliquable vers la mini-fiche déjà codée (mini-
histogramme). Coût de dev faible : réutilise le composant existant, zéro nouvelle
métrique, résout directement l'ancrage des mots interprétatifs.

**B — Radar sur les mêmes axes (priorité basse, pas écartée)**
Mêmes métriques, rayon = niveau ordinal (COMMON=0 → VERY_RARE=3). Un tirage ordinaire
donne un polygone plat, un tirage à traits inhabituels donne une forme en pointes —
lecture visuelle immédiate de la forme statistique du tirage. Risque à traiter :
confusion possible entre grande aire du radar et probabilité de gain future (jamais
un signal prédictif) — nécessiterait un rappel méthodologique plus appuyé que pour de
simples badges. À envisager une fois le set de métriques A stabilisé et validé par
l'usage, pas avant.

Décision de Christophe : les deux vont dans la todolist, A en priorité plus haute que B.

## Garde lexical ajouté et testé (30/09/2026, ~1h45)

`guard_interpretive_words()` ajouté à `llm_compose_test.py` : vérifie que tout mot de
rareté employé dans le texte (rare, très rare, notable, exceptionnel, frappant,
remarquable, peu courant, inhabituel — avec gestion de la négation, "ce n'est pas rare")
est justifié par AU MOINS un fait fourni atteignant ce niveau de `rarity`. Testé hors
ligne sur 4 cas synthétiques (mot justifié, inflation, négation, aucun fait rare
disponible) : comportement correct dans les 4 cas.

Testé en conditions réelles sur EM-26077 et EM-2011053 : garde numérique OK, garde
lexical OK sur les deux articles — aucun faux positif, aucune inflation manquée.

**Défaut trouvé en lisant le texte (le garde ne l'attrape pas, ce n'est pas son rôle)** :
le modèle recopie littéralement les noms de code de l'enum anglais dans la prose
française — "classée VERY_RARE", "ce qui est dans la zone COMMON", "relève du COMMON" —
au lieu de mots français. Cause : `evidence_block()` transmet `rareté={f['rarity']}`
avec la valeur brute de l'enum. Le site a pourtant déjà la traduction (`RARITY_FR` dans
`dist/draws.js` : COMMON→"courante", UNCOMMON→"peu courante", RARE→"rare",
VERY_RARE→"très rare"). **Correctif prioritaire pour la prochaine session** :
1. Traduire `rarity` en français dans `evidence_block()` avant de le donner au modèle
   (réutiliser le mapping `RARITY_FR`, le porter côté Python si besoin).
2. Interdire explicitement dans le prompt de citer un nom de code d'enum (majuscules,
   underscore) — n'employer que le mot français correspondant.

Note technique secondaire, non bloquante : les motifs `INTERPRETIVE_TERMS` n'ont pas de
frontière de mot (`\b`) en fin de motif, donc "rares?" matcherait aussi la sous-chaîne
"RARE" à l'intérieur d'un token comme "VERY_RARE" ou un mot comme "rareté" employé au
sens générique (non testé en pratique ce soir, mais à corriger par prudence — ajouter
`\b` des deux côtés et/ou exclure les tokens tout en majuscules).

## Le garde lexical passe, le texte reste imprécis (30/09/2026, ~1h50) — 4 cas vérifiés

Le garde numérique + lexical passe sur EM-26077 et EM-2011053, mais une lecture fine
révèle que « pas d'incohérence détectée » ne veut pas dire « article correct ». Quatre
défauts précis relevés par Christophe, vérifiés contre les facts JSON :

1. **Métriques redondantes présentées comme indépendantes.** `main.span` (38,
   UNCOMMON) et `main.mean_gap` (9,5, UNCOMMON) partagent EXACTEMENT le même
   `class_size`/`p_class` — mean_gap = span/4 (5 numéros → 4 écarts), c'est la même
   information sous deux noms. `main.sorted_gaps` (VERY_RARE) est légitimement plus
   fin (répartition exacte des 4 écarts, pas seulement leur somme). Le texte cite
   span et mean_gap comme deux preuves distinctes de "resserrement" — en plus de
   qualifier une étendue de 38 (proche du max possible ~49) de "resserrée" alors
   qu'elle est UNCOMMON et plutôt du côté dispersé.

2. **Dénombrement incohérent dans le texte.** Sur EM-2011053, une phrase dit "trois
   écarts simples de 1, 2 et 5" puis, juste après, "écarts ordonnés 1-2-5-7" (4
   valeurs). Le fait source a bien 4 écarts (35,42,47,48,50 → gaps 7,5,1,2). Le garde
   numérique ne l'attrape pas : le 7 apparaît ailleurs dans le texte, donc aucun
   "nombre non autorisé" n'est détecté — c'est une incohérence interne entre deux
   formulations du même fait, pas un nombre inventé.

3. **Rareté d'un fait appliquée à un autre.** Sur EM-2011053, le texte dit "cette
   configuration est classée parmi les formes VERY_RARE, avec 2,0 % pour le maximum
   dans une même dizaine et 7,1 % pour occuper deux dizaines" — or `max_same_decade`
   (2,0 %) et `occupied_decades` (7,1 %) sont UNCOMMON tous les deux. Le VERY_RARE
   appartient à un TROISIÈME fait, `decade_counts` (profil complet "0-0-0-1-4",
   classe 0,10 %), jamais cité avec son propre chiffre — le modèle a emprunté son
   label et l'a justifié avec les chiffres des deux autres métriques.

4. **Pourcentages sans dénominateur ni nature.** Le texte donne "2,0 %" et "7,1 %"
   sans dire s'il s'agit de `p_class` ou `tail`, ni la taille de la classe/du domaine
   — le badge de rareté seul ne remplace pas cette précision, rien dans le prompt ne
   l'impose actuellement.

### Diagnostic (formulation de Christophe)

Le garde lexical vérifie la cohérence LOCALE entre un mot et les champs de rareté
disponibles quelque part dans les faits ; il ne garantit pas qu'une phrase associe le
bon badge à la bonne métrique, ni que les définitions mathématiques des métriques
citées ensemble sont réellement indépendantes. Le prochain verrou doit vérifier la
RELATION métrique → valeur → rareté → formulation, phrase par phrase, en particulier
quand une phrase synthétise plusieurs métriques à la fois — pas seulement la présence
des nombres et des mots.

### Pistes pour ce verrou (à concevoir la prochaine session, pas codé ce soir)

- Extraction structurée : demander au modèle de citer chaque fait avec un tag explicite
  (ex. `[F.main.decade_counts]`) à côté de chaque affirmation de rareté, pour permettre
  un appariement automatique mot ↔ fait_id plutôt qu'un "au moins un fait quelque part".
- Table de redondance déclarée entre métriques dérivées les unes des autres (span ↔
  mean_gap, etc.) pour interdire de les citer comme deux preuves indépendantes.
- Imposer dans le prompt : chaque pourcentage doit être immédiatement suivi de sa base
  (classe de X/Y, ou queue) et de son fact_id.
- Vérification de cohérence interne : si le texte énonce une liste de N valeurs pour un
  fait (ex. écarts ordonnés), vérifier que toute reformulation ultérieure de ce même
  fait dans l'article cite bien les N mêmes valeurs.
