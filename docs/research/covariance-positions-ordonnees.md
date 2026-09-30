# Covariance des positions ordonnées — note de recherche v0.1

Source primaire : Coronel-Brizio, Hernández-Montoya, Rapallo et Scalas,
« Statistical auditing and randomness test of lotto k/N-type games » (2008),
https://arxiv.org/abs/0806.4595, équations 9 et 10.

## Objet

Pour un tirage uniforme de `k` numéros distincts dans `1..N`, on note
`Y₁ < … < Yₖ` les valeurs classées. La matrice théorique relie **les positions
d'un même tirage**, sans introduire le temps :

```text
E[Yᵢ] = (N + 1)i / (k + 1)
Cov(Yᵢ,Yⱼ) = min(i,j) [k - max(i,j) + 1] (N + 1)(N - k)
               / [(k + 1)²(k + 2)]
```

La matrice entière dépend du régime `k/N`. La sortie conserve néanmoins
`game_id` et `component = main` : l'audit empirique ne fusionnera jamais deux
jeux sous prétexte qu'ils partagent une formule. Le rapport refuse aussi un
couple jeu/régime principal non qualifié. Elle n'est donc pas une valeur
nouvelle à calculer pour chaque tirage. Une covariance **observée** demande un
ensemble de tirages homogènes et une convention explicite de période et
d'estimation ; elle reste distincte de la matrice attendue sous le modèle.

## Lien avec l'étendue

`span = Yₖ - Y₁`. Par conséquent :

```text
E[span] = E[Yₖ] - E[Y₁]
Var(span) = Var(Yₖ) + Var(Y₁) - 2 Cov(Y₁,Yₖ)
```

La covariance des deux extrêmes intervient dans la loi de l'étendue ; ces
grandeurs ne sont pas des indices indépendants d'une anomalie. Le programme
[`engine/order_position_covariance.py`](../../engine/order_position_covariance.py)
calcule les fractions exactes. Les tests confrontent **chaque cellule** à
l'énumération de petits univers, puis la variance d'étendue à la loi exacte
indépendante déjà calculée par `engine/laws_recurrence.py`.

| Régime | `Cov(Y₁,Yₖ)` | `E[span]` | `Var(span)` |
|---|---:|---:|---:|
| EuroMillions, 5/50 | 255/28 | 34 | 510/7 |
| Loto ancien, 6/49 | 1075/196 | 250/7 | 5375/98 |
| Loto actuel, 5/49 | 550/63 | 100/3 | 4400/63 |
| Keno actuel, 16/56 | 380/867 | 855/17 | 3800/289 |

Les régimes historiques sont des séries distinctes : Loto 6/49 puis 5/49,
Keno 20/70 puis 16/56. EuroMillions conserve les tirages principaux 5/50 ;
les étoiles relèvent de leurs propres régimes et ne sont pas incluses ici.
Le numéro Chance du Loto n'entre pas dans la matrice des numéros principaux.

Exemple local :

```sh
python3 engine/order_position_covariance.py --game-id euromillions --picks 5 --domain 50
```

## Suite avant dictionnaire ou article

1. Estimer la matrice historique sur des tirages d'un **seul régime à la fois**,
   avec effectif, période, source, éventuelles lacunes et méthode d'estimation.
2. Qualifier séparément un audit statistique : écart des moyennes par rapport à
   la matrice théorique, incertitude, simulations de calibration, fenêtres
   choisies à l'avance et multiplicité des tests. Un résultat extrême ne prouve
   pas à lui seul un défaut du mécanisme.
3. Si l'objectif porte sur la dépendance entre tirages successifs, définir une
   **autocovariance avec décalage** distincte : elle n'est pas la matrice ci-dessus.
4. Préparer un article de fond montrant pourquoi l'étendue et les positions
   ordonnées sont reliées, sans transformer l'audit en méthode de prédiction.

Les identifiants `theory.main.order_position_covariance@v1` et
`history.main.order_position_covariance@v1` sont des noms logiques. Les clés
publiées devront être préfixées par jeu, par exemple
`loto.history.main.order_position_covariance@v1`, et porter le régime exact.
Aucun badge, fait de tirage ou article n'est publié par cette étude.
