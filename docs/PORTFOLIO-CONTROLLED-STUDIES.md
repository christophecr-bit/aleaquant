# Études avec références RANDOM — enveloppe 1.0 · 10 octobre 2026

L'enveloppe `engine/study.py` exécute une nouvelle génération principale et ses
témoins RANDOM, puis les évalue ensemble. Les études et moteurs signés du premier
jalon restent conservés ; leurs archives ne reçoivent pas de témoin rétroactif.
Les anciens fichiers actifs deviennent des versions sélectionnables dans l'Atlas.

## Configurer, lancer et reprendre

Les exemples sont `configs/controlled/overlap-random-v1.json` et
`configs/controlled/evolution-random-v1.json`. Une configuration contient la
question et le protocole de l'expérience principale, les graines de contrôle,
les rôles de pool et les limites globales. `same_pool` est obligatoire ;
`full_domain` est un contrôle distinct optionnel. Modifier la configuration puis
utiliser un nouveau dossier ; la reprise refuse une configuration ou une source
modifiée. Les protocoles non pris en charge sont refusés.

L'interpréteur scientifique local utilisé pour ce jalon est
`/Users/chris/.local/share/aleaquant-pipeline-venv/bin/python`. Remplacer `python`
ci-dessous par cet interpréteur, ou par un environnement avec les dépendances
scientifiques du dépôt.

```sh
python engine/study.py validate --study-config configs/controlled/overlap-random-v1.json
python engine/study.py run --study-config configs/controlled/overlap-random-v1.json --run-dir runs/controlled/ma-nouvelle-etude --stop-after-main 4
python engine/study.py status --run-dir runs/controlled/ma-nouvelle-etude
python engine/study.py run --study-config configs/controlled/overlap-random-v1.json --run-dir runs/controlled/ma-nouvelle-etude --stop-after-controls 4
python engine/study.py run --study-config configs/controlled/overlap-random-v1.json --run-dir runs/controlled/ma-nouvelle-etude --stop-after-comparison-batches 1
python engine/study.py run --study-config configs/controlled/overlap-random-v1.json --run-dir runs/controlled/ma-nouvelle-etude --stop-after-confirmation-batches 1
python engine/study.py run --study-config configs/controlled/overlap-random-v1.json --run-dir runs/controlled/ma-nouvelle-etude
```

Les arrêts volontaires renvoient le code 2, une complétion le code 0 et un refus
le code 1. Chaque reprise ajoute du travail après le checkpoint ; elle ne rejoue
pas les constructions ou batchs déjà achevés. Les bornes sont explicites et la
progression est journalisée en JSON. `--output` choisit une projection alternative.
L'export final est refusé avant la confirmation complète des finalistes et témoins.
Ces commandes génèrent localement les résultats ; elles ne déploient pas le site.

## Deux rôles de contrôle

- RANDOM mêmes pools : même nombre de grilles, coût, règles, contraintes et pools
  explicites que le plan principal. Pour l'ablation, les dix graines correspondent
  aux dix graines des quatre poids. Pour l'évolution, les témoins ont leurs graines
  distinctes des parents et opérateurs ; aucune différence appariée n'est inventée.
- RANDOM domaine complet : choix dans les ensembles explicites 1–50 et 1–12.
  Ce contrôle mesure aussi le changement de pool et reste présenté séparément.

Chaque contrôle est un candidat aléatoire sans optimisation par score. Il est
exclu des parents, survivants, finalistes et choix de graines. Si une contrainte
ou garantie demandée échoue, l'étude le signale et refuse ce contrôle ; elle ne
recherche pas une meilleure graine ni un meilleur résultat MC.

La qualification recalcule les propriétés et vérifie méthode, objectifs nuls,
règles, coût, grilles, pools, versions, sources et environnement. Le MC commun
doit appartenir à cette génération et à l'ensemble complet de contenus évalués :
même protocole, graine, flux et empreinte. Un ancien MC ou un poids nul glouton
présenté comme RANDOM est refusé. Les intervalles Wilson individuels ne constituent
pas un test de différence entre portefeuilles ; les différences restent descriptives.

## Démonstrations réellement exécutées

| Expérience | Plan principal | Témoins mêmes pools | Témoins domaine complet | Contenus distincts | Comparaison | Confirmation |
|---|---:|---:|---:|---:|---|---|
| Pénalité de recouvrement | 40 constructions, 4 poids × 10 graines | 10 | 10 | 58 | 20 000 tirages communs | 20 000 tirages indépendants, 5 finalistes + 20 témoins |
| Descendants | 5 parents + 24 nouveaux enfants | 10 | 10 | 49 | 5 000 tirages communs | 5 000 tirages indépendants, 5 enfants finalistes + 20 témoins |

Les deux exécutions ont été arrêtées puis reprises aux phases de génération,
contrôles, comparaison et confirmation. Tous les témoins sont qualifiés et
confirmés. La preuve conditionnelle exhaustive concerne 30 030 cas pour les pools
15/5. Le domaine complet dépasse ce plafond de preuve ; il reste explicitement
non certifié lorsque cette preuve n'est pas demandée.

Résultats locaux actifs : `dist/data/portfolio_study.json` (60 fiches) et
`portfolio_evolution.json` (49). Les index conservent deux exécutions chacun,
dont les anciennes cohortes de 40 et 29 sans RANDOM. Les portefeuilles principaux
reproduisent les graines et méthodes déclarées ; retrouver un même contenu lors
d'une nouvelle exécution reproductible est attendu et ne constitue pas un import
des anciennes évaluations. Chaque nouveau lot a ses évaluations communes propres.

Identités de ces démonstrations :

- Ablation : `run:56eff3fab937745ad46c3bf559f756e68f30fe5ec53f27018d8c74a46419856c`.
- Évolution : `run:8339bc43e680e863488a5c658e8e23fc24f6e0fa25679fb78d9a724a5fad8d39`.

Les compromis du plan principal restent ceux observés précédemment : renforcer
la pénalité peut réduire la somme des intersections au carré tout en dégradant
leur maximum ou une couverture. Les mutations ne produisent pas automatiquement
de meilleurs enfants. Le front déclaré ne comprend pas cette somme au carré.
L'Atlas sépare maintenant l'effet du poids, le benchmark face à RANDOM sur mêmes
pools et l'effet du pool. Aucun résultat n'est une prévision de tirage.

## Validation du jalon

112 tests des moteurs de portefeuille, 18 tests d'évolution et 22 tests de
l'enveloppe/qualification réussis. Les projections complètes ont été recalculées
à l'identique depuis leurs exécutions signées. Vingt-cinq fichiers scientifiques
et archives historiques contrôlés par SHA restent inchangés, ainsi que l'Atlas
scientifique et les 53 définitions de métriques. Les sources `portfolio_*.py` et
`evolution/` des anciens runs restent reprenables et exportables.

Les dettes TD-PORT-001/002 sont résolues pour ces deux protocoles ; leur portée
n'englobe pas de nouveaux jeux ou opérateurs non implémentés.
