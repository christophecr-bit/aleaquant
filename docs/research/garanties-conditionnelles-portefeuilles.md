# Portefeuilles à garantie conditionnelle — note de cadrage

Date : 1er octobre 2026 · Auteur : AleaQuant · Statut : axe de recherche de l'Atlas ; aucun produit de roues à la demande

## Sens de « 3 if 4 of 10 »

[Lottery Post](https://www.lotterypost.com/wheels) emploie « X if Y of Z » :
si au moins `Y` numéros tirés appartiennent au pool choisi de `Z` numéros,
au moins une des grilles du portefeuille contient `X` numéros tirés. C'est
une garantie **conditionnelle sur le pool**, pas une méthode pour prévoir quels
numéros y entreront. La garantie ne tient que si **toutes les grilles annoncées
sont jouées** ; les filtrer peut la détruire.

Formellement, pour un pool `P` de taille `p`, des grilles principales `B` de
taille `k` et des nombres `x ≤ y ≤ p`, le certificat `x if y of p` vérifie :

```text
pour tout S ⊆ P tel que |S| = y,
    il existe une grille B telle que |S ∩ B| ≥ x.
```

Si la condition vaut pour `y`, elle vaut aussi pour davantage de numéros
gagnants dans `P`. La vérification peut énumérer les `C(p,y)` sous-ensembles
`S` et fournir un contre-exemple en cas d'échec. Pour un grand pool, il faudra
un autre certificat ou une preuve par solveur ; l'échec à trouver un
contre-exemple par échantillonnage ne suffit pas. La recherche du plus petit
nombre de grilles pour un tel certificat est un **lotto design** ; lorsque
`x=y`, elle rejoint le problème classique des covering designs. Voir
[Bougard et al., *The lotto numbers L(n,3,p,2)*](https://onlinelibrary.wiley.com/doi/abs/10.1002/jcd.20075)
et [Gordon et al., *New constructions for covering designs*](https://arxiv.org/abs/math/9502238).

## Exemple Loto : pool 10, grilles de 5, budget 25

`3 if 4 of 10` oblige à examiner `C(10,4)=210` scénarios possibles de quatre
numéros corrects dans le pool. Cela diffère d'une simple couverture de
triplets : il suffit qu'une grille recoupe chaque scénario en **au moins trois**
numéros, sans nécessairement contenir chacun des `C(10,3)=120` triplets.

Le [catalogue Pick 5 de Lottery Post](https://www.lotterypost.com/wheels/pick5)
affiche une roue `3 if 4 of 10` à **7 grilles**, une `4 if 5 of 10` à **14**
et une `4 if 4 of 10` à **52**. Ce sont des offres listées, pas des minima
prouvés par ce catalogue ; le contenu détaillé est réservé aux membres et ne
sera pas repris. On peut toutefois prouver indépendamment que `4 if 4 of 10` est
impossible avec 25 grilles : chaque grille de 5 contient seulement 5
quadruplets, alors qu'il faut couvrir les 210 quadruplets du pool ; il faut
donc au moins `ceil(210/5)=42` grilles. Avec 25 grilles, le bon objectif est à
choisir : garantie plus forte sous une condition plus forte, plusieurs grilles
garanties à un rang inférieur, recouvrement secondaire, ou compromis de ces
critères. Le nombre 25 ne définit pas à lui seul l'optimisation.

Même si les 25 grilles certifient `3 if 4 of 10`, elles ne rendent pas plus
probable la présence de quatre bons numéros dans le pool. Sous le modèle
uniforme du Loto 5/49, cette condition « au moins 4 dans un pool fixé de 10 »
a une probabilité de `(C(10,4)C(39,1)+C(10,5))/C(49,5) = 8442/1906884`,
soit environ **0,443 %**. Ce calcul ne dépend pas de l'organisation des
grilles ; celle-ci détermine uniquement ce qui est garanti **si** la condition
se réalise. Il ne faut pas confondre la probabilité d'une grille exacte, la
probabilité de la condition, et le rang obtenu une fois la condition satisfaite.
Pour une garantie purement combinatoire, un modèle sur `{1,…,10}` peut être
renommé bijectivement avec n'importe quel pool de 10 numéros sans perdre sa
garantie. Cela ne transporte pas les contraintes liées à la valeur numérique,
aux décades ou à l'historique.

### Premier certificat AleaQuant

Le vérificateur exhaustif indépendant `engine/conditional_guarantees.py`
contrôle une roue candidate sur les **210** scénarios `4 of 10` et conserve un
témoin du pire cas. Le solveur facultatif `tools/solve_conditional_wheel.py`
cherche le **plus petit nombre** de grilles parmi les `C(10,5)=252` grilles
possibles. Pour `3 if 4 of 10`, SciPy/HiGHS a trouvé **7 grilles**, une borne
duale de **7** et un écart nul en **8,452 s** lors du premier essai. Ce cas
dispose donc d'une preuve d'optimalité par le solveur ; la roue produite a été
revérifiée séparément sur les 210 scénarios. Le résultat reproductible et ses
empreintes sont archivés dans
[`conditional-wheel-10-5-4-3.json`](conditional-wheel-10-5-4-3.json).
La borne de comptage élémentaire seule n'était que **4** et n'aurait pas
permis cette conclusion. Cette preuve concerne ce petit cas précis, pas tous
les pools ni toutes les contraintes.

L'intérêt est d'expliquer la **frontière combinatoire** : combien de grilles
sont nécessaires pour une garantie formulée sans ambiguïté, sous quelle
condition et avec quel certificat. Le rang bas correspondant à trois numéros
Loto peut rapporter peu au regard de la mise de sept grilles. Sans barème
versionné, composante Chance et comparaison du coût au paiement, aucune
conclusion économique n'est établie. Cette étude ne justifie ni stratégie de
jeu ni vente de roues.

## Du nombre de correspondances au rang de gain

Un certificat sur les **numéros principaux** n'est pas automatiquement un
certificat de rang : le Loto dépend aussi du numéro Chance, EuroMillions des
étoiles, et Keno de la taille de grille et de son barème. Le contrat de preuve
doit donc porter séparément :

- la condition sur les numéros principaux et, si utile, la composante secondaire ;
- le minimum de correspondances garanti sur au moins une grille, voire le
  nombre minimal de grilles atteignant un seuil ;
- le rang ou paiement brut minimal **seulement** après application d'un
  barème versionné et vérification de tous les tirages compatibles ;
- le nombre de grilles, leur coût total, l'empreinte des grilles et le
  certificat ou le premier contre-exemple.

Une garantie peut être montrée comme une **matrice condition → correspondance
minimale** avant toute traduction en euros. Sur le site, la phrase doit rester
explicite : « si au moins 4 des 5 numéros tirés sont dans votre pool de 10,
au moins une des grilles certifiées en contient 3 ». Il ne faut écrire ni
« trois bons numéros garantis au prochain tirage » ni « gain garanti » sans
la condition complète et le barème applicable.

## Suite de l'axe de recherche

1. Étendre la matrice de petites conditions `x if y of p` en archivant pour
   chacune le statut de preuve, une solution, les bornes et le coût de calcul.
   Ne pas extrapoler la vitesse du cas 10/5 à tous les pools.
2. Pour des budgets fixés, comparer les portefeuilles candidats à `RANDOM`
   sous les mêmes contraintes, puis confronter la garantie au coût de toutes
   les grilles. Une heuristique ou Monte-Carlo explore ; seul un contrôle
   exhaustif ou un certificat formel autorise le mot « garantie ».
3. Conserver la multiplicité minimale de grilles à chaque seuil, puis étudier les composants
   Chance/étoiles et barèmes historiques par régime. Keno exige une cohorte
   par taille de grille et objectif de rang.
4. Étendre les tests à d'autres cohortes et à leurs limites de taille. Le cas
   archivé vérifie déjà que retirer l'une quelconque des sept grilles détruit
   la garantie. Ne pas copier les
   listes de grilles réservées aux membres de Lottery Post.

La garantie combinatoire décrit la **répartition conditionnelle** de résultats
entre plusieurs grilles. Elle ne prédit pas le prochain tirage, ne change pas
la probabilité intrinsèque d'une grille et ne démontre aucun rendement positif.
