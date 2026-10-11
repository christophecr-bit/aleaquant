# Plan documentaire — portefeuilles · v1.0 · 10 octobre 2026

Objectif : permettre de lire une étude sans connaître les noms de paramètres du
programme. Règle : [SITE-DOCUMENTATION-RULES.md](SITE-DOCUMENTATION-RULES.md).
Périmètre initial : notions utilisées par l'Atlas et le pipeline de recherche.
L'inventaire du catalogue comporte 43 notions observées. Le glossaire ajoute les
racines « numéro », « étoile » et « paire » : 46 définitions, avec prérequis de
lecture et liens complémentaires distincts. L'Atlas général reste à inventorier.
Le premier lot intègre le glossaire localement. Les quatorze sujets ci-dessous
sont des dossiers à traiter dans le pipeline éditorial canonique, pas des articles
publiés. Le site utilise les ancres du glossaire tant que les articles ne sont pas
approuvés et importés. Les versions et empreintes du glossaire sont dans le registre
généré `dist/comprendre/documentation.json` ; les dossiers d'articles restent dans
`../aleaquant-editorial-agents`.

## Parcours et questions

| Ordre | Notion / question du lecteur | Page | Format |
|---|---|---|---|
| 1 | Qu'est-ce qu'un portefeuille de grilles ? | `/comprendre/portefeuilles/` | Parcours d'entrée |
| 2 | Dans quel ensemble les grilles sont-elles choisies ? | `/comprendre/pool/` | Mini-article |
| 3 | Que signifie partager des numéros ? | `/comprendre/recouvrement/` | Mini-article + exemple |
| 4 | Que couvrent les paires et triplets ? | `/comprendre/couverture/` | Mini-article |
| 5 | Comment un score récompense ou pénalise une grille ? | `/comprendre/score/` | Mini-article manipulable |
| 6 | Comment les grilles sont-elles ajoutées une par une ? | `/comprendre/construction/` | Mini-article |
| 7 | Comment étudier l'effet d'un paramètre (« ablation ») ? | `/comprendre/etude-parametre/` | Mini-article |
| 8 | À quoi sert le témoin RANDOM ? | `/comprendre/reference-random/` | Mini-article |
| 9 | Que modifie une mutation ? | `/comprendre/mutation/` | Mini-article manipulable |
| 10 | Comment deux portefeuilles produisent-ils un enfant ? | `/comprendre/croisement/` | Mini-article + schéma |
| 11 | Pourquoi un enfant peut-il ne pas être retenu ? | `/comprendre/selection/` | Mini-article |
| 12 | Que mesure une simulation Monte-Carlo ? | `/comprendre/monte-carlo/` | Mini-article |
| 13 | Sous quelles conditions une garantie est-elle vraie ? | `/comprendre/garantie-conditionnelle/` | Mini-article |
| 14 | À quoi sert une graine de génération ? | `/comprendre/graine/` | Mini-article |
| Accès rapide | Définition des mots rencontrés | `/comprendre/glossaire/` | Glossaire avec liens |

## État et critères de livraison

- Les URL des articles sont des destinations prévues. Leur ouverture dépend de la
  validation éditoriale ; aucun lien de l'Atlas ne pointe vers ces pages en attente.
- Le registre de dépendances contrôle les versions et l'accès public à tous les
  prérequis avant publication. Le glossaire généré localement ne satisfait pas
  encore ce contrôle. Les articles et leurs dossiers restent non publiés.
- Lot direct : définitions de paire de numéros, paire de grilles, recouvrement,
  paires communes, pénalité, poids, ablation, graines appariées et compromis, puis
  construction, mutation, croisement, sélection, RANDOM, MC et garantie.
- Lot éditorial : chaque dossier répond à une question et demande un exemple,
  les preuves, la portée et les risques d'interprétation. Rédaction et publication
  suivent le pipeline canonique, avec approbation humaine du SHA exact.
- Les futurs exemples expliquent la somme des intersections au carré et les
  mutations, sans fabriquer des résultats ni un héritage de garantie.
- Les tableaux conservent chiffres, limites et protocole inspectable ; la lecture
  commence par leur sens, pas par les paramètres internes.
- Navigation réelle depuis l'accueil et l'Atlas, ancres du glossaire, version des
  contenus et affichage mobile sont vérifiés.

## Extension du plan au reste du site

Le même inventaire doit couvrir les notions des autres rubriques : équiprobabilité,
classes de combinaisons, distributions, histogrammes, quantiles, rareté et lois
historiques. Le premier lot donne leurs définitions rapides lorsqu'elles sont
nécessaires ; des mini-articles dédiés seront priorisés dans PB-016. L'inventaire
des 34 métriques historiques et des 19 métriques de portefeuille doit rattacher
chaque définition à sa notion, sans créer artificiellement un article par ID.
