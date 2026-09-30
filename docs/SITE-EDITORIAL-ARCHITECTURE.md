# Architecture éditoriale du site — maquette locale v0.2

Date : 30 septembre 2026 · Auteur : AleaQuant · Statut : **proposition locale, non déployée**

## Décision : le prochain chantier

Le prochain sujet à développer est **le gabarit éditorial de l’accueil et des rubriques,
alimenté par des contenus approuvés**. La maquette locale est dans
`prototypes/editorial-home/index.html`. Elle montre la hiérarchie et les cartes ;
elle ne remplace pas encore l’accueil du Worker. Le raccordement aux données réelles
et le choix d’un éventuel portage Astro viennent après validation visuelle et éditoriale.

## Carte du site proposée

| Rubrique | Question du lecteur | Contenus | Destination actuelle |
|---|---|---|---|
| Tirages | Que montre ce résultat ? | Fiche par tirage, analyse, article approuvé | `/tirages/` puis jeu et identifiant/date |
| Comprendre | Que signifie cette mesure ? | Explication, expérience, brève pédagogique | Mini-expérience et dictionnaire de l’accueil actuel |
| Atlas & géométries | Quelle forme ont les tirages et les portefeuilles ? | Atlas, visualisation, article de fond | Aperçu hétérogène ; contrat et cohortes dans `ATLAS-GEOMETRIES-ARCHITECTURE.md` |
| Recherche & méthode | Comment le sait-on ? | Note de recherche, veille, méthode, limites | Méthode actuelle ; notes à qualifier |

Le **Journal** est un fil transversal de publications approuvées, pas une cinquième
rubrique concurrençant les quatre parcours. Le sélecteur de jeu, le calendrier et
les archives restent dans « Tirages ». Une page de tirage garde son URL stable et
peut accueillir un article approuvé sans que l’article remplace les faits calculés.

## Gabarit commun

```text
Accueil
├─ promesse et illustration AleaQuant
├─ derniers tirages (données fraîches, par jeu)
├─ rubriques
│  ├─ introduction : nom, question, courte description, lien vers l’archive
│  └─ cartes de contenu : 1 contenu phare + 1 ou 2 contenus secondaires
└─ rappel de méthode

Carte : type · jeu/discipline · date → titre → chapô → visuel → lien/statut
Page de tirage : résultat → article approuvé éventuel → faits et mini-histogrammes
               → historique comparable → méthode/provenance → navigation
```

Une carte n'est publiée que si son objet cible existe et est publiable. Les sujets
prévus dans la maquette portent explicitement « à préparer » et n'ont pas de lien.
Le type est explicite : `article`, `analyse_tirage`, `breve`, `experience`,
`note_recherche` ou `reference`. Une future entrée de manifeste devrait porter
au minimum : `id`, `type`, `rubrique`, `titre`, `chapo`, `date`, `url`, `statut`,
`jeu` facultatif, `visuel` et son texte alternatif, et références de provenance.
Pour un article, l'URL et le titre viennent de la version humaine approuvée, liée
aux empreintes du brouillon et du Research Pack. Pour une analyse de tirage, le jeu,
la règle et le résultat viennent des faits calculés. Ne pas recopier manuellement
des chiffres dans une carte produite automatiquement.

Les cartes ont une structure HTML/CSS commune. Le visuel peut être une illustration
originale, un SVG descriptif calculé ou une texture, mais jamais un graphique qui
suggère une mesure absente. Le libellé « très rare » se rapporte toujours à une
classe de métrique définie, jamais au tirage dans son ensemble.

## Mini-histogrammes sur les pages de tirage

Le rendu statique des fiches doit insérer les mini-histogrammes à partir de la loi
exacte du **même régime** que le tirage. Le trait orange situe la valeur observée ;
la carte conserve la fréquence et la rareté de la **classe exacte**. Pour rester
lisible et limiter le poids HTML, jusqu'à 48 barres voisines sont affichées, avec
regroupement visuel si la loi est plus longue. Ce regroupement ne change aucun
calcul ni verdict de rareté. Les lois catégorielles et les métriques dépourvues de
loi n'ont pas de mini-histogramme ; leur carte textuelle reste visible.

Depuis la correction locale du 30 septembre, chaque métrique scalaire dont la loi
est disponible pour le bon régime peut recevoir ce repère ; le Loto
`LO-20260928` en affiche 18. Les signatures non ordonnées restent textuelles.
La vérification de régime doit précéder le rendu ; une loi absente ou
discordante conduit à omettre le graphe, pas à afficher un dessin trompeur.

## Frontières d'architecture

- `aleaquant-data` fournit les tirages et révisions ; le moteur local produit les
  lois et les faits. Aucun LLM ne modifie ces nombres.
- `aleaquant-editorial-agents` organise propositions, preuves, rédaction, contrôles
  et approbation humaine. Le batch existant du site reste une voie distincte tant
  que son intégration n'est pas qualifiée.
- `aleaquant-web` construit les pages et les index statiques. Le Worker Cloudflare
  sert les artefacts après une décision de publication ; Wrangler n'est pas un CMS.
- `prototypes/editorial-home/` sert aux essais visuels locaux. Aucune carte de
  brouillon ne doit y être présentée comme article déjà publié.

## Étapes de la prochaine itération

1. Relire la maquette sur desktop et mobile, choisir les noms définitifs des
   rubriques et le nombre de cartes visibles par rubrique.
2. Construire un manifeste éditorial généré uniquement depuis les articles
   approuvés, les fiches publiées et quelques ressources explicitement curatées.
3. Alimenter le fil de tirages depuis la dernière révision connue **par jeu** ;
   supprimer le snapshot daté de la maquette.
4. Décider du portage de ce gabarit dans le site actuel ou dans Astro après mesure
   du coût de génération, du nombre d'assets et du rendu mobile.
5. Qualifier le premier Atlas de portefeuilles et ses articles d'introduction selon
   `ATLAS-GEOMETRIES-ARCHITECTURE.md` : qualifier des références Loto,
   homogénéiser leur présentation avec EuroMillions/Keno et expliquer les
   limites des comparaisons. La construction de roues à la demande est différée.

Ni cette maquette ni les mini-histogrammes ne changent la chaîne d'approbation,
les faits ou le sens des probabilités. Comprendre le hasard n'est pas prédire le
prochain tirage.
