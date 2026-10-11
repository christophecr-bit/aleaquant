> Extension moteur 1.1 : l'entité Étude, le mode prototype_greedy et la
> comparaison/confirmation indépendantes sont maintenant décrits dans
> [PORTFOLIO-STUDIES.md](PORTFOLIO-STUDIES.md). Les nombres de profils et
> définitions ci-dessous décrivent le premier jalon 1.0, conservé séparément.

# Pipeline de portefeuilles 1.0 — premier jalon local

Le pipeline vit dans `aleaquant-web/engine`, à partir de l'import existant.
Il réutilise `portfolio_geometry`, le dictionnaire commun `dist/metrics.json`,
les conventions de contenu canonique et le viewer du Prompteur. Le laboratoire
et ses campagnes sont lus sans modification ; aucun projet parallèle,
historique de tirages, achat ou déploiement n'est lancé.

Les six exemples du ZIP sont conservés dans `portfolio_pipeline.json` avec
leurs résultats d'origine. Ils sont aussi vérifiés et réévalués par le nouveau
moteur, avec une autre graine, dans le run local. Les fiches distinguant ces
deux exécutions évitent d'attribuer un ancien résultat à un nouveau contenu.

## Contrat

`configs/portfolios/milestone-v1.json` enregistre 13 profils versionnés.
`engine/portfolio_profile_v1.schema.json` décrit le profil ; les validations
croisées de `portfolio_contract` restent actives sous `python -O`.

- `game` fixe EuroMillions 5/50+2/12 à 2,50 €, sans options. Autres règles,
  tarifs et options sont refusés en 1.0, plutôt que silencieusement ignorés.
- `pool` contient les listes explicites ou `seeded_sample`, les cardinalités
  et la graine. Le tirage du pool est indépendant de la construction des grilles.
- `constraints` porte nombre de grilles, budget **maximal**, unicité et deux
  plafonds d'intersection distincts (numéros/étoiles). Le coût **utilisé** est
  `grid_count × unit_price_eur` ; il peut être inférieur au plafond. Une garantie
  demandée sans preuve accessible dans les bornes déclarées est refusée.
- `objectives` porte des préférences pondérées, pas des obligations.
- `search` fixe random, greedy ou enumerate, graines, propositions par étape,
  nombre de candidats, plafond total de propositions et de secondes. Population
  supérieure à 1 et opérateurs évolutionnaires sont refusés pour ce jalon.
- `evaluation` fixe métriques, taille, graine indépendante, batch, durée et
  budget d'énumération de preuve. La recherche sélectionne uniquement sur la
  géométrie exacte ; aucun événement MC ne choisit les graines ou les candidats.

Le schéma est strict et versionné. Les preuves de capacité et certaines bornes
sur les intersections donnent des impossibilités accessibles. Une recherche
bornée infructueuse reste `search_exhausted` ; elle n'est jamais une preuve
d'impossibilité. La preuve combinatoire et l’estimation Monte-Carlo restent distinctes.

## Objectifs et métriques

Le dictionnaire commun garde ses 34 définitions de grilles et reçoit 12
définitions de portée `portfolio`, versionnées, avec unité, direction, méthode
et version d'évaluateur. Les identifiants des grilles ne sont pas réécrits.

Le score glouton final vaut :

`w_pairs × paires distinctes + w_triples × triplets distincts`

`− w_numbers × dispersion² dans le pool des numéros`

`− w_stars × dispersion² dans le pool des étoiles`

`+ w_concentration × Σ overlap_numbers²`

`− w_overlap_numbers × Σ overlap_numbers² − w_overlap_stars × Σ overlap_stars²`.

Chaque somme d'intersection porte sur les paires **non ordonnées** de grilles.
La dispersion² est la somme des écarts au carré à la fréquence moyenne dans
le pool, y compris les valeurs non utilisées. La dispersion affichée pour les
comparaisons utilise le domaine complet 50/12 ; ce dénominateur est déclaré.
`minimize_overlap` porte donc explicitement sur les deux composantes, avec
agrégation `sum_squares` et poids séparés. L'intersection moyenne seule ne
départage pas deux ensembles dont les fréquences individuelles sont fixées.

Balanced, Low overlap et Concentrated expriment une intention ; les poids
décident du score réellement exécuté. Enumerate est une méthode exhaustive de
construction du pool, compatible seulement si toutes ses grilles tiennent dans
le budget. Une famille Coverage n'est pas une preuve de garantie ou d'optimalité.

## Preuves, évaluation et comparaison

Une condition déclare : le pool contient **exactement X** des cinq numéros et
**exactement Y** des deux étoiles tirés. L'objectif demandé est : il existe
une **même grille** avec **au moins R** numéros et **au moins S** étoiles.
Le témoin peut varier entre tirages. Une preuve énumère toutes les issues sous
cette hypothèse, y compris les valeurs tirées hors pool quand X<5 ou Y<2.
Elle conserve contenu, pool, hypothèses, seuils, nombre de cas, probabilité
exacte de la condition et version de l'évaluateur. Au-delà des limites, une
garantie facultative reste `not_checked` ; une garantie obligatoire est refusée.
`0+2` seul n'est pas un rang gagnant. La preuve parentale ne sera jamais héritée.

Le nouvel évaluateur utilise des tirages uniformes sans remise, communs à tous
les contenus concrets, avec RNG PCG64 et graine séparée. Comptages de gains
sur chaque grille, IC95 Wilson et moyenne de grilles gagnantes sont exportés.
La moyenne théorique est calculée analytiquement. Le jackpot utilise exactement
`m / [C(50,5)×C(12,2)]` ; aucun remboursement ni montant de gain n'est évalué.
Les IC sont ponctuels, sans correction de multiplicité : ce jalon exploratoire
ne démontre aucune supériorité d'une famille.

Deux cohortes différentes sont exportées :

1. `same_pool` : mêmes règles, taille, coût utilisé et listes du pool, avec
   candidats RANDOM dans ce pool.
2. `different_pools` : mêmes règles, taille et coût utilisé, pools libres,
   incluant RANDOM sur le domaine complet. Le nombre effectif de pools est
   déclaré : à 55 € le registre actuel en contient un seul. Le résultat reflète à la fois le
   choix du pool et la construction ; il n'isole pas l'effet de la construction.

Les fronts non dominés sont calculés sur paires/triplets (maximiser), dispersion
des numéros et intersection maximale (minimiser). Ils sont des compromis selon
ces quatre critères, jamais un classement économique ou par MC. Les budgets
45/50/55 € sont alternatifs. D'autres budgets sont possibles par `grid_count`
et `budget_max_eur`, avec les limites déclarées ; le test 17,50 € en est un cas.

## Persistance et graphe

Un profil versionné, une exécution de génération, un contenu concret, une
exécution MC/protocole et une preuve de garantie sont des objets distincts.
Le graphe utilise des identifiants de contenu et est vérifié sans cycle.
Les mêmes grilles obtenues par plusieurs profils ont un seul nœud portefeuille
et une seule évaluation par protocole. Les fiches gardent leurs contextes de
génération comme alias, sans les présenter comme des répétitions indépendantes.
Chaque génération initiale porte opérateur, paramètres, graine et parents vides.

`runs/portfolios/<run>/generation-checkpoint.json` sauvegarde chaque profil
terminé. Après interruption à l'intérieur d'un profil, ce profil borné est
reconstruit avec ses mêmes graines ; les profils terminés sont conservés.
`generation.json` est immuable, avec empreintes configuration et code.

Le checkpoint MC conserve RNG, compteurs et frontière durable dans le même
écrit atomique ; reprise sans double comptage, sous verrou local. Les versions,
environnement, protocole, code et ensemble de contenus doivent correspondre.
Le budget de temps est vérifié aux frontières de batches ; un batch déjà
commencé se termine puis est sauvegardé. Un run interrompu n'exporte aucun
résultat final. `latest-evaluation.json` désigne une exécution terminée ; les
évaluations précédentes restent dans leur répertoire.

L'Atlas reçoit une archive immuable `dist/data/portfolio_runs/<run-id>/catalogue.json`
et une projection active `dist/data/portfolio_search.json`. L'export émet une
fiche JSON et les grilles CSV par contexte. L'ancien Atlas et les membres du
ZIP restent préservés.

## Commandes

Depuis `/Users/chris/aleaquant/aleaquant-web`, utiliser l'environnement existant :

```sh
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_pipeline.py validate
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_pipeline.py generate --include-references
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_pipeline.py evaluate --stop-after-batches 1
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_pipeline.py evaluate
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_pipeline.py compare
/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python engine/portfolio_pipeline.py export
```

`run --include-references` enchaîne generate/evaluate/export. `--config` choisit
un autre registre ; `--run-dir` isole une campagne dans ce même projet. Pour
réévaluer un contenu gelé, `evaluate --seed N --draws N` crée un autre protocole
sans modifier la génération. Rejouer le même protocole achevé ne recalcule pas
les tirages. Choisir un nouveau dossier lorsque code ou configuration changent.

Étape suivante : introduire des mutations (remplacement de numéro, échange
entre grilles, remplacement de grille) avec revalidation/repreuve, puis
sélection/diversité et croisement. Aucune interface ne prétend les exécuter en
version 1.0. Un échantillon de confirmation distinct sera obligatoire si le MC
entre un jour dans la sélection.
