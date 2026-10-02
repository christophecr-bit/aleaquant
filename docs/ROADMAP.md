# Roadmap produit AleaQuant — 2 octobre 2026

Auteur : AleaQuant · v0.4 · 2 octobre 2026

Cette feuille décrit les capacités que les lecteurs et l'équipe doivent pouvoir
utiliser. Les choix durables de structure sont consignés dans les documents
d'architecture ; les composants techniques encore à construire sont suivis dans
[`TECHNICAL-DEBT.md`](TECHNICAL-DEBT.md). Les sujets de recherche et d'écriture
appartiennent au comité éditorial.

Le classement relatif des livraisons est dans le
[`backlog produit`](PRODUCT-BACKLOG.md). La TODO opérationnelle, les décisions à
instruire et la dette d'ingénierie restent des registres séparés.

## Site et données

- **Accueil éditorial structuré** : présenter les dernières analyses de tirages,
  puis des contenus rangés dans Tirages, Comprendre, Atlas & géométries et
  Recherche & méthode. Les cartes conduisent à des contenus réels et approuvés.
- **Archive de tirages exploitable** : consulter résultats et faits ensemble,
  filtrer, trier, choisir les colonnes et télécharger un export documenté.
- **Pages de tirage pour les trois jeux** : accéder par une URL stable au résultat,
  à ses faits et visualisations, à l'historique comparable et à un éventuel article.
  Pour Keno, l'accès doit couvrir ses deux régimes sans créer une page statique par
  tirage.
- **Historique des évolutions du modèle** : consulter des notes courtes lorsqu'une
  métrique, une règle, un claim de méthode, un moteur ou une correction change les
  données ou leur interprétation. La référence versionnée est tenue dans
  [`aleaquant-data/docs/MODEL-CHANGELOG.md`](../../aleaquant-data/docs/MODEL-CHANGELOG.md).
- **Flux RSS des publications** : permettre aux lecteurs de suivre les nouveaux
  articles et brèves publiés. Le flux ne contient que des contenus publics,
  approuvés et accessibles par URL canonique.
- **Newsletter hebdomadaire** : proposer une sélection commentée des publications
  récentes. Elle complète le RSS sans le recopier à l'identique ; l'abonnement est
  volontaire et la désinscription simple.

## Pilotage privé

- **Console unique à onglets** : administration et review dans le même outil privé.
  Suivi, Tirages & calculs, Lots & agents, Review, Publication et Système partagent
  un journal d’exécution. Catalogue et livraison progressive dans
  [ADMIN-CONSOLE-ARCHITECTURE.md](../../aleaquant-editorial-agents/docs/ADMIN-CONSOLE-ARCHITECTURE.md)
  (PB-014). Cadrage demandé, pas encore livré.

- **Vue « Suivi » dans la console de review** : donner une lecture immédiate de la
  fraîcheur des tirages et calculs pour chaque jeu, des retards et erreurs de
  pipeline, de la veille RSS/recherche, du nombre d'articles par étape éditoriale,
  de la file d'approbation et des derniers déploiements. Les métriques de trafic et
  d'exécution Cloudflare y sont datées, attribuées à leur source et distinguées.
- **Brief personnel quotidien** : résumer les événements et éléments à surveiller
  depuis la dernière journée, puis l'envoyer chaque matin par courriel privé avec
  des liens vers les détails et la console. La console reste la source de vérité ;
  le brief est un signal pratique, sans action automatique ni appel LLM nécessaire.
  Son mécanisme d'envoi est distinct de la newsletter publique.

## Éditorial

- **Application éditoriale responsive** : consulter un lot de brouillons sur
  ordinateur ou téléphone, lire le texte avec ses preuves et contrôles, approuver,
  refuser avec une remarque, ou corriger en créant une version distincte.
- **Publication avec rubrique** : après approbation humaine du brouillon exact,
  proposer une action Publier, demander la rubrique, afficher une prévisualisation
  et intégrer l'article au site sous Tirages, Comprendre, Atlas & géométries ou
  Recherche & méthode. Préparer aussi les métadonnées éditoriales, vérifier le titre
  de page et la hiérarchie HTML des titres, et appliquer les consignes de la checklist
  SEO revue avant chaque campagne de rédaction/publication. Le Journal en fournit un
  fil transversal. Aucun agent ne publie seul.
- **Récit associé aux tirages** : proposer progressivement un article par tirage
  quand les résultats, les faits, les preuves et leurs empreintes sont validés.
  Le lot quotidien reste soumis au choix humain.
- **Illustrations éditoriales du MVP** : préparer pour les premiers articles des
  visuels originaux de data science, avec une composition en panneaux, graphiques,
  matrices de couverture et texture légère. La planche de référence est
  [`portfolio-geometry-visual-reference.jpg`](references/portfolio-geometry-visual-reference.jpg) ;
  elle sert de direction visuelle seulement. Ses nombres, légendes et conclusions
  sont des exemples de maquette et ne doivent jamais être repris comme résultats.

Architecture du site : [`SITE-EDITORIAL-ARCHITECTURE.md`](SITE-EDITORIAL-ARCHITECTURE.md).
Workflow agentique et critères de qualité : feuille de route du dépôt
[`aleaquant-editorial-agents`](../../aleaquant-editorial-agents/docs/roadmap-editorial-agentique.md).

## Atlas et recherche

- **Atlas des géométries** : présenter des portefeuilles de référence qualifiés,
  leurs recouvrements et leurs limites, avec comparaisons sous budget commun et
  référence RANDOM. Commencer par qualifier les cohortes Loto et compléter les
  familles EuroMillions à 6 grilles et Keno à 10 numéros ; publier leurs définitions,
  provenance, protocole et niveau de preuve. Les roues personnalisées restent hors
  de cette première livraison.
- **Garanties conditionnelles** : illustrer quelques cas exacts sur des pools,
  avec bornes et certificats, en commençant par des cas pédagogiques comparés à RANDOM
  sous budget identique ; différer la construction personnalisée à la demande.
- **Études à instruire par le comité éditorial** : loteries « k parmi C » dans le
  monde ; multiplicité des tests et Benjamini–Hochberg ; covariance des positions
  ordonnées et métriques de forme ; calcul HPC et géométrie des portefeuilles.
  Aucun sujet ne devient un article avant la collecte des preuves et la validation
  humaine.

Architecture de l'Atlas : [`ATLAS-GEOMETRIES-ARCHITECTURE.md`](ATLAS-GEOMETRIES-ARCHITECTURE.md).
Les briefs éditoriaux détaillés sont dans le manifeste du comité du dépôt
[`aleaquant-editorial-agents`](../../aleaquant-editorial-agents/docs/editorial-launch-manifest.md).
