# Portefeuilles à garantie conditionnelle — note de cadrage

Date : 1er octobre 2026 · Auteur : AleaQuant · Statut : recherche, aucun moteur ni classement publiés

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
et une `4 if 4 of 10` à **52**. Ce sont des offres listées, **pas des minima
prouvés ici** ; le contenu détaillé est réservé aux membres et ne sera pas
repris. On peut toutefois prouver indépendamment que `4 if 4 of 10` est
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

## Étude proposée pour l'Atlas

1. Implémenter un vérificateur déterministe indépendant du générateur :
   validation des grilles, parcours exhaustif des conditions finies, matrice
   `x if y of p`, témoin de pire cas et contre-exemple en cas d'échec.
2. Pour Loto `p=10, k=5`, comparer les 25-grilles candidates et `RANDOM`
   sous les mêmes contraintes ; chercher aussi le **nombre minimal de grilles**
   pour une garantie cible, sans déclarer un optimum non démontré.
3. Ajouter multiplicité minimale de grilles à chaque seuil, puis composants
   Chance/étoiles et barèmes historiques par régime. Keno exige une cohorte
   par taille de grille et objectif de rang.
4. Tester qu'enlever une grille peut invalider le certificat, que le renommage
   bijectif du pool le conserve, et que les pires cas sont réellement atteints.
   Ne pas copier les listes de grilles réservées aux membres de Lottery Post.

La garantie combinatoire décrit la **répartition conditionnelle** de résultats
entre plusieurs grilles. Elle ne prédit pas le prochain tirage, ne change pas
la probabilité intrinsèque d'une grille et ne démontre aucun rendement positif.
