# Études de portefeuilles — contrat 1.0, moteur 1.1

Documentation v1.1 : l'expérience initiale ci-dessous reste archivée. La nouvelle
[enveloppe avec témoins RANDOM](PORTFOLIO-CONTROLLED-STUDIES.md) complète le
protocole sans modifier ses sources signées ni ses résultats historiques.

Une **Étude** définit une question, les métriques pertinentes, un profil de
base, les paramètres fixes, un axe de variation, les graines appariées, les
répétitions, les bornes, la comparaison et la confirmation finale. Ses
références décrivent les expériences de départ ; leurs grilles et anciennes
estimations ne deviennent pas les résultats de la nouvelle génération.

Le contrat strict est `engine/portfolio_study.schema.json` ; les contrôles
croisés sont dans `portfolio_study_contract.py` et restent actifs sous `-O`.
Le premier protocole implémenté est une ablation appariée sur
`objectives.minimize_overlap.numbers`, avec pools **explicites** constants.
Un autre axe, un autre opérateur ou une règle non prise en charge est refusé.
Pour d'autres questions, il faudra ajouter un protocole testé ; modifier la
configuration suffit pour les budgets, pools, poids, graines et répétitions
pris en charge, dans les bornes déclarées.

## Reprise du constructeur du prototype

`build.py`, `profiles.json` et le README du ZIP sont conservés et inspectés.
Le prototype initialise `random.Random(pool_seed)`, permute les 50 numéros et
12 étoiles, puis prend des préfixes triés de ces permutations. L'étude conserve
explicitement le pool du cas Balanced 50 :

- numéros : 6, 7, 9, 13, 15, 17, 22, 30, 35, 40, 42, 43, 48, 49, 50 ;
- étoiles : 2, 7, 9, 10, 11.

La méthode `prototype_greedy` utilise `random.Random(seed)` et **1 200
propositions par ajout**. Elle tire cinq numéros et deux étoiles, rejette les
doublons et les violations de contraintes, puis garde le premier candidat de
score maximal. Une fenêtre interrompue n'est jamais présentée comme terminée.

Le score incrémental exécuté est exactement :

`8 × nouveaux triplets + 3 × nouvelles paires`

`− 0,9 × somme des occurrences courantes des numéros du candidat`

`− 0,8 × somme des occurrences courantes de ses étoiles`

`− poids_overlap × somme des intersections de numéros au carré`.

Ce mode est distinct du mode `greedy` du premier jalon, qui pénalise une
dispersion au carré. Ses poids ne sont donc pas interchangeables sans préciser
le mode. Le constructeur original isolé et la nouvelle implémentation sont
comparés dans les tests ; avec la graine 1035 et le poids 0,7, les vingt grilles
Balanced 50 du ZIP sont reproduites à l'identique, sans rejouer ses 500 000
simulations. Les graines de l'étude réelle sont nouvelles.

Balanced et Spread sont deux réglages de la même construction gloutonne.
Le recouvrement maximal de 1 observé dans les anciens Spread était un résultat,
pas une contrainte dure. Dans la nouvelle étude, les plafonds 5 numéros/2 étoiles
permettent toute intersection valide ; seul le poids **souple** des numéros
varie. Complete conserve l'énumération exhaustive existante. Clustered dans le
prototype impose un noyau de trois numéros ; il reste une référence distincte
de l'intention CONCENTRATED du mode générique, qui ne fixe pas ce noyau.

## Nouvelle étude enregistrée

Configuration : `configs/studies/minimize-overlap-20x15x5-v1.json`.

- 20 grilles uniques, coût utilisé et maximal 50 €, pools 15/5 ci-dessus ;
- poids numéros `0`, `0.35`, `0.7`, `1.4`, autres poids et règles constants ;
- dix graines communes aux quatre réglages : 2026101000 à 2026101009 ;
- 40 constructions avant déduplication, 24 000 propositions chacune ;
- maximum 30 s par construction, 600 s par appel du run aux frontières sûres ;
- preuves optionnelles : 100 000 cas au maximum, 2 millions de contrôles
  grille/cas ; ici les 30 030 issues 5+2 internes au pool sont accessibles ;
- comparaison : 20 000 tirages communs, graine 2810010, batches de 2 000 ;
- confirmation : 20 000 nouveaux tirages, graine 2910010, batches de 2 000 ;
- MC : maximum 30 s par appel de phase, sauvegarde à chaque batch terminé.

Les règles et bornes du profil de portefeuille sont réutilisées. Chaque
candidat est contrôlé et sa géométrie calculée depuis ses grilles. Les preuves
sont recalculées pour son contenu concret ; aucune référence ni simulation ne
transmet une garantie à une nouvelle construction.

Le dictionnaire commun reçoit histogrammes d'intersections, occurrences et
événements MC déjà calculés. Paires/triplets ont des dénominateurs 105/455 dans
le pool et 1225/19600 dans le domaine entier. Les intersections sont comptées
sur les 190 paires non ordonnées de grilles. Les fréquences incluent les zéros
sur le domaine entier, et l'analyse donne séparément celles du pool. Les dix
paires d'étoiles possibles dans le pool et leurs occurrences sont enregistrées.

## Répétitions et finalistes

Le tableau résume moyenne, minimum, maximum et écart-type population des dix
constructions par poids. Cet écart-type décrit la variation entre graines ;
il ne constitue pas un intervalle de confiance Monte-Carlo.

Les différences sont calculées **poids B moins témoin 0, pour la même graine**,
puis résumées sur les dix graines. La synthèse conserve le nombre de graines
favorables, défavorables et inchangées, ainsi que les effets mixtes. Elle ne
conclut jamais à partir d'une seule graine.

Les finalistes sont choisis uniquement par les paires/triplets couverts
(maximiser), l'écart-type des occurrences des numéros et l'intersection maximale
(minimiser). Un quota représente chaque poids : de préférence le front global,
sinon le front propre à ce poids. Puis le front global remplit les places, au
plus douze contenus distincts. L'ordre déterministe est paires décroissantes,
triplets décroissants, dispersion croissante, intersection maximale croissante,
SHA du contenu puis identifiant. Les exceptions de quota sont explicites.
Le front global complet reste enregistré même au-delà de douze contenus.

La somme des intersections au carré, qui est l'axe étudié, reste une mesure
distincte : elle n'entre pas dans ces quatre critères du front. Un candidat
sur ce front n'est donc pas présenté comme optimal pour cette somme. Les
quotas gardent aussi un représentant des autres poids pour la confirmation.

L'exécution `runs/studies/overlap-20261009-v1` a produit 40 constructions et
38 contenus distincts, tous nouveaux par rapport aux six références du ZIP.
Les 960 000 propositions ont été exécutées. Les 38 contenus ont été comparés
sur les 20 000 tirages communs ; cinq finalistes ont reçu la confirmation
indépendante. Les 38 preuves distinctes ont chacune énuméré 30 030 issues
internes au pool. Elles sont conditionnelles aux pools et ne garantissent pas
un gain sur tous les tirages du jeu.

Sur les dix graines, les sommes d'intersections au carré moyennes sont
512,2 / 509,2 / 508,0 / 506,7 pour les poids 0 / 0,35 / 0,7 / 1,4.
Le maximum d'intersection moyen passe cependant de 2,6 à 3,0 ; la couverture
moyenne des triplets passe de 199,0 à 198,4. Au poids 1,4, deux graines perdent
une paire couverte. Le score pénalise une somme, pas le maximum, et la
construction gloutonne ne revient pas sur ses choix : il existe donc des
compromis, sans amélioration uniforme.

Le MC n'influence jamais cette sélection. Les probabilités marginales, leurs
IC95 Wilson et les différences arithmétiques sur tirages communs sont
descriptifs ; sans covariance par tirage, ils ne fournissent pas de test
significatif d'une différence. Le nouvel échantillon de confirmation porte
uniquement sur les finalistes. Les deux graines et empreintes de tirages restent
visibles. Un gain n'est pas un bénéfice ; jackpot exact, aucun remboursement.

## Exécution et progression

Depuis `/Users/chris/aleaquant/aleaquant-web` :

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_study.py validate --study-config configs/studies/minimize-overlap-20x15x5-v1.json
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_study.py run --study-config configs/studies/minimize-overlap-20x15x5-v1.json
```

**Cette dernière commande réalise une nouvelle exécution**, avec son dossier
unique imprimé dès le départ. Pour reprendre ce même run ou consulter l'état :

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_study.py run --study-config configs/studies/minimize-overlap-20x15x5-v1.json --run-dir runs/studies/MON-DOSSIER
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_study.py status --run-dir runs/studies/MON-DOSSIER
```

Dupliquer la configuration, changer son identifiant/version et les paramètres
souhaités, valider puis lancer `run --study-config nouvelle-config.json`.
Les champs non pris en charge sont refusés. Utiliser `--run-dir` pour une reprise,
jamais pour remplacer une définition ou un moteur différents.

Progression JSON : poids/graine, constructions terminées/attendues,
propositions, puis batches MC de chaque rôle. Arrêts courts disponibles :
`--stop-after-constructions N`, `--stop-after-comparison-batches N` et
`--stop-after-confirmation-batches N`. La sortie 2 signale un état incomplet,
reprenable ; aucun export final n'est publié avant la confirmation achevée.
Une recherche infructueuse reste `search_exhausted` et ne démontre aucune
impossibilité. Les limites de temps sont vérifiées à des frontières sûres : une
construction ou un batch déjà commencé finit son contrôle avant sauvegarde.

## Persistance et Atlas

La définition et l'identité StudyRun sont immuables. La génération sauvegarde
chaque construction. Les deux phases MC utilisent les checkpoints atomiques,
RNG et compteurs existants. Une signature modifiée de code, configuration ou
environnement refuse la reprise. Un verrou empêche les runs concurrents dans
le même dossier ; l'index des études est mis à jour sous verrou distinct.

Les profils ont quatre versions de réglage ; chaque GenerationRun enregistre
sa surcharge de graine. Le graphe relie Study, StudyRun, versions de profil,
générations, contenus, évaluations de comparaison/confirmation et preuves.
Les références sont des nœuds de provenance distincts et ne sont pas des
parents de mutation. Les générations initiales ont des parents vides.

Chaque exécution possède un identifiant propre, même si la configuration et
les graines sont réutilisées. Les archives sont dans
`dist/data/portfolio_study_runs/<run-id>/catalogue.json`, l'index append-only
logique dans `dist/data/portfolio_studies.json`, la projection active dans
`dist/data/portfolio_study.json`. Les JSON/CSV sont dans le dossier `exports` du
run. Les anciens portefeuilles et l'ancienne étude restent consultables ; seules
les projections actives et l'index sont mises à jour atomiquement.

L'Atlas `/portefeuilles/` propose Études, Pipeline initial et ZIP séparément,
avec un sélecteur d'exécution d'étude, les paramètres, les résumés appariés,
les fiches et le viewer. Aucune publication distante n'est effectuée.

Étape suivante : remplacement d'un numéro, échange entre grilles et remplacement
d'une grille, puis sélection générationnelle/diversité et enfin croisements.
Ces opérateurs reprendront les mêmes validations, preuves et évaluations ;
aucune garantie parentale ne sera héritée.
