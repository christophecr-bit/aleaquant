# Évolution de portefeuilles — enveloppe 1.0

Documentation v1.1 : le premier run ci-dessous reste archivé. La nouvelle
[enveloppe contrôlée](PORTFOLIO-CONTROLLED-STUDIES.md) ajoute et qualifie les
témoins RANDOM dans une nouvelle exécution, sans modifier le moteur signé.

Cette extension ajoute des opérateurs au pipeline de validation, géométrie,
preuve et évaluation existant. Elle conserve l'étude d'ablation précédente et
ses sources signées. Son entrée est `engine/evolve.py` ; son contrat strict est
`engine/evolution/study.schema.json`, avec les contrôles croisés du module
`contract.py`. Aucun historique de tirages n'intervient dans la construction.

## Configuration et opérateurs

La configuration `configs/evolution/overlap-descendants-v1.json` définit la
question, les métriques, cinq contenus de départ et leur source immuable,
le profil physique commun, les graines, la population, les générations,
les limites, la sélection et les deux échantillons d'évaluation.

Les cinq parents sont les finalistes géométriques de la première étude. Leurs
grilles et identités sources restent conservées. Les objectifs sont normalisés
au profil commun de poids 0,7 ; les contraintes physiques restent 20 grilles,
budget 50 €, mêmes pools explicites 15/5. Leurs estimations MC précédentes
n'interviennent dans aucune sélection.

Quatre opérateurs versionnés sont exécutés :

- `replace_number_v1` remplace un numéro d'une grille par un numéro du pool absent
  de cette grille ;
- `swap_numbers_v1` échange deux numéros exclusifs entre deux grilles, en
  conservant les fréquences globales de numéros ;
- `replace_grid_v1` remplace une grille complète par une nouvelle grille du pool ;
- `grid_crossover_v1` assemble un portefeuille depuis l'union des grilles de deux
  parents distincts. Une grille exclusive de chaque parent est incluse, ce qui
  atteste les deux contributions et un contenu différent de chacun des parents.

Une proposition est une tentative, sans reprises cachées ni réparation de
contrainte. Un enfant invalide, inchangé ou déjà rencontré est rejeté et le
rejet est enregistré. Chaque nouvel enfant valide repasse par `validate_grids`,
`proof_for`, `make_record` et `check_record`. Une garantie obligatoire non prouvée
refuse l'enfant ; une garantie parentale ne se transmet jamais.

La démonstration planifie deux générations de huit mutations, puis une génération
de huit croisements, avec population cinq et maximum 24 propositions. Les trois
mutations alternent à chaque génération. La graine de chaque proposition est
2026101100 + son index (0 à 23) ; elle pilote aussi le choix de parents. Ce budget
court démontre les opérateurs, sans établir une supériorité d'une méthode.

L'exécution `runs/evolution/overlap-descendants-20261009-v1` est terminée :
24 enfants nouveaux, aucun rejet sur ces propositions, 29 contenus avec les
cinq parents. Elle a exécuté six remplacements de numéro, six échanges,
quatre remplacements de grille et huit croisements. Tous les contenus ont
leurs propres preuves et évaluations ; cinq enfants ont été confirmés.

La population finale conserve les cinq parents initiaux : aucun enfant ne les
a remplacés sur les quatre critères déclarés. Le mélange de grilles par
croisement peut défaire la complémentarité créée par le constructeur glouton.
Dans cette courte exécution, les huit croisements couvrent 95 à 99 paires et
176 à 187 triplets, contre 105 paires et 199 à 200 triplets pour les parents.
Ces observations motivent de futurs opérateurs tenant mieux compte de la
géométrie, mais ne suffisent pas à condamner les croisements en général.

## Sélection, comparaison et confirmation

À chaque génération, les parents actuels et les nouveaux enfants valides forment
les entrants. La sélection recalcule les quatre critères exacts : maximiser
paires/triplets, minimiser l'écart-type des fréquences de numéros dans le domaine
complet et l'intersection maximale. Elle remplit des couches Pareto successives
avec des contenus distincts. Dans une couche, le départage suit ces critères,
puis SHA et identifiant. La somme des intersections au carré est mesurée mais
n'est pas un critère de sélection de ce protocole.

Tous les enfants acceptés, y compris les non-survivants, restent dans le catalogue
et passent l'évaluation. Les cinq parents sont évalués dans le même nouveau lot
de comparaison : 5 000 tirages communs, graine 3010010. Au plus cinq finalistes
choisis parmi tous les enfants sur la géométrie reçoivent la confirmation :
5 000 nouveaux tirages, graine indépendante 3110010. Ce sont des échantillons
descriptifs ; aucune performance MC ne choisit les parents, survivants ou
finalistes. Les IC95 Wilson marginaux ne constituent pas un test de différences.

## Commandes et reprise

Depuis `/Users/chris/aleaquant/aleaquant-web` :

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/evolve.py validate --study-config configs/evolution/overlap-descendants-v1.json
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/evolve.py run --study-config configs/evolution/overlap-descendants-v1.json
```

Le run imprime un nouveau dossier unique. Pour une autre étude, dupliquer la
configuration, changer id/version et les paramètres pris en charge, puis valider
et lancer avec son chemin. Les sources de parents sont des catalogues immuables
et leurs empreintes de fichier et de contenu doivent correspondre.

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/evolve.py status --run-dir runs/evolution/MON-DOSSIER
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/evolve.py run --study-config configs/evolution/overlap-descendants-v1.json --run-dir runs/evolution/MON-DOSSIER
```

Arrêts courts disponibles : `--stop-after-proposals N`,
`--stop-after-generations N`, `--stop-after-comparison-batches N` et
`--stop-after-confirmation-batches N`. Une sortie 2 signale une exécution
incomplète, reprenable. Une sauvegarde signée intervient après chaque proposition,
y compris rejetée, et chaque sélection ; les évaluations sauvegardent chaque
batch. La graine par proposition permet de reprendre au milieu d'une génération
sans changer ses parents ni ses choix. Un verrou empêche deux runs concurrents
dans le même dossier. Le plafond de 600 secondes s'applique aux frontières sûres ;
une unité déjà engagée finit puis sauvegarde. Aucun export final n'est publié
avant la confirmation achevée.

Les signatures propres incluent les nouveaux modules et le moteur partagé.
Changer une configuration, une source parent ou un moteur refuse la reprise :
lancer un nouveau dossier. Les nouveaux fichiers sont dans `engine/evolution/`
pour conserver l'inventaire signé de l'étude d'ablation précédente.

## Persistance et Atlas

La projection active est `dist/data/portfolio_evolution.json` ; chaque catalogue
est conservé dans `dist/data/portfolio_evolution_runs/<run-id>/catalogue.json`.
L'index `portfolio_evolutions.json` conserve les exécutions sans les écraser.
Les JSON/CSV de chaque candidat restent dans le dossier `exports` du run.

La source Evolution de l'Atlas affiche les générations, entrants, survivants,
rejets, opérateurs et parents, puis les preuves et les deux rôles MC. Le graphe
relie étude, exécution, générations, portefeuilles, sélections, évaluations et
preuves. Les liens `derived_from` enregistrent les parents par contenu ; le
croisement en comporte deux. Les parents de départ conservent leurs références
à l'étude d'ablation. Les sources Études, Pipeline initial et ZIP restent
consultables séparément, avec le même viewer de grilles.
