# Backlog produit AleaQuant

Auteur : AleaQuant · v0.16 · 11 octobre 2026

Ce registre ordonne les résultats produit à construire. La priorité est une
proposition de travail, pas une échéance promise. Les capacités du produit sont
décrites dans [`ROADMAP.md`](ROADMAP.md) ; les choix durables de structure dans
les documents d'architecture ; les composants et risques d'ingénierie dans
[`TECHNICAL-DEBT.md`](TECHNICAL-DEBT.md). Les tâches d'exploitation sont dans
[`OPERATIONAL-TODO.md`](OPERATIONAL-TODO.md), et les explorations à instruire dans
[`TASKS.md`](TASKS.md).

Une entrée sort du backlog lorsqu'elle est livrée et vérifiée, ou lorsqu'une
décision explicite l'écarte. Les tâches de réalisation restent dans la dette ou la
TODO opérationnelle, avec un lien vers l'ID produit concerné.

| ID | Priorité proposée | Statut | Résultat attendu pour l'utilisateur | Critère de sortie |
|---|---|---|---|---|
| PB-001 | P0 | Structure courte retenue ; contenu à valider | Accueil éditorial organisé en rubriques et cartes compréhensibles, avec les derniers tirages mis en avant. | Textes et sélection de l'accueil court approuvés, destinations réelles, derniers tirages sourcés, recette mobile et lot figé. Première v0 livrée manuellement avec Codex selon `V0-MANUAL-RELEASE.md`. |
| PB-002 | P0 | En cours | Consulter EuroMillions, Loto et Keno depuis une URL stable avec résultat, faits et visualisations cohérents. | Les trois jeux sont accessibles ; les deux régimes Keno sont distingués ; l'historique Keno ne crée pas des milliers de pages statiques. |
| PB-003 | P1 | Partiel local | Lire une analyse éditoriale attachée à un tirage et demander une correction par sa référence stable. | Article approuvé, rubrique, identité jeu/date et `article_id` consultables ; versions et approbations distinctes, claims et preuves contrôlés, intégration locale vérifiable. Les références sont affichées localement ; l'archivage durable des éditions reste à qualifier (TD-EDIT-002). |
| PB-004 | P1 | Prototype | Relire sur ordinateur ou téléphone, approuver, refuser avec remarque et corriger une publication sans perdre les versions précédentes. | Console privée reliée au flux de publication rubricée, avec nouvelle empreinte après correction et approbation explicite avant intégration. |
| PB-005 | P1 | À qualifier | Explorer des familles de portefeuilles et comprendre leurs recouvrements, couvertures et limites. | Cohortes Loto et références EuroMillions/Keno accompagnées de leur protocole, provenance et référence RANDOM à budget égal. |
| PB-006 | P2 | Recherche cadrée | Comprendre quelques garanties conditionnelles exactes sur des pools et des rangs. | Cas pédagogiques calculés, certifiés indépendamment et présentés avec bornes et limites ; aucune promesse prédictive. |
| PB-007 | P2 | À instruire | Explorer résultats et faits historiques en tableau et les réutiliser dans ses propres analyses. | Filtres, pagination et exports CSV/JSON documentés avec schéma, régime, provenance et version des calculs. |
| PB-008 | P0 | À préparer pour le MVP | Comprendre ce qui a changé dans le modèle AleaQuant et si cela modifie les fiches publiées. | Registre versionné couvrant métriques, claims de méthode, règles/régimes, moteurs et corrections ; mini note lisible, jeux concernés, compatibilité, validation et plage recalculée publiés après revue humaine. |
| PB-009 | P1 | À cadrer | Produire des articles lisibles, bien structurés et techniquement compréhensibles par les moteurs de recherche. | Avant une campagne de rédaction/publication, la checklist Google Search Central est revue et datée ; chaque publication possède des titres et métadonnées adaptés, une hiérarchie de titres sémantique, des rubriques/tags contrôlés et un statut d'indexation cohérent avec sa valeur éditoriale. Les règles SEO ne peuvent modifier ni les faits ni les conclusions scientifiques. |
| PB-010 | P1 | Partiel — collecte RSS/arXiv livrée | Repérer des sujets éditoriaux à partir d'une veille web vérifiable, avec un angle AleaQuant et des preuves à collecter. | Socle livré : cinq flux quotidiens, SQLite séparé, versions, provenance, doublons, cache, statut et dossier optionnel pour le Scout. Guide : `../../aleaquant-editorial-agents/docs/RESEARCH-WATCH.md`. Restent la curation multirequêtes, les sources ouvertes et vérifiées, les contrepoints et la qualification des sujets. Aucun résultat de recherche n'est pris pour une preuve scientifique sans vérification par l'Evidence Planner. La collecte n'exécute ni LLM ni rédaction ; fournisseur de recherche configurable et tests hors ligne. |
| PB-011 | P1 | À cadrer | Suivre depuis la console privée l'état des opérations AleaQuant et recevoir chaque matin un courriel personnel des changements, retards et points à traiter. | Une vue « Suivi » présente la fraîcheur et le dernier succès de chaque pipeline de tirages, les retards par jeu, l'état des faits/pages/déploiements, la santé des flux de veille, les recherches et leur coût si disponible, ainsi que les articles par étape jusqu'à la file d'approbation. Un digest déterministe, daté, idempotent et consultable dans la console est envoyé chaque matin à l'adresse privée configurée ; les métriques de fréquentation et d'exécution Cloudflare indiquent source, période et fraîcheur. Le fournisseur d'envoi et le comportement quand le Mac dort (rattrapage au réveil ou agrégat cloud limité) sont décidés ; les secrets restent côté serveur, les échecs sont visibles et relançables. Aucune publication ou action automatique n'est déclenchée. |
| PB-012 | P1 | À cadrer | S'abonner aux nouvelles publications AleaQuant dans un lecteur de flux RSS. | Un flux public valide recense les publications réellement publiées, avec URL canonique, titre, date, rubrique et résumé ; aucun brouillon ou contenu privé n'y apparaît. Le flux est vérifié avec un lecteur RSS et les pages restent accessibles sans abonnement. |
| PB-013 | P2 | À cadrer | Recevoir chaque semaine une sélection éditoriale AleaQuant, distincte du flux exhaustif des publications. | Une newsletter périodique assemble une sélection de contenus publiés et approuvés, avec liens canoniques et un court éditorial ; inscription explicite, désinscription fonctionnelle et gestion minimale des données d'abonnés sont vérifiées avant tout envoi. Le service d'envoi et l'archivage web sont choisis avant implémentation. |
| PB-014 | P1 | À concevoir | Piloter les opérations dans la même console privée que Review, avec plusieurs onglets, sans terminal ni intervention de Codex. | Navigation commune : Suivi, Tirages & calculs, Lots & agents, Review, Publication, Système ; journal transversal. Voir le [cadrage canonique](../../aleaquant-editorial-agents/docs/ADMIN-CONSOLE-ARCHITECTURE.md). Choisir le jeu, le régime, la période ou les tirages ; lancer la récupération, le recalcul des faits et la reconstruction des profils/pages via les outils existants ; suivre progression, logs, résultats et erreurs. Prévisualiser le périmètre et les conséquences avant un recalcul forcé, comparer les sorties avant installation et signaler les articles à revalider. Les tâches persistent après fermeture du navigateur ; reprise ou relance après interruption selon les capacités du batch. Les lancements concurrents avec launchd sont maîtrisés. Aucune publication automatique ; les snapshots approuvés restent protégés. |

| PB-015 | P2 | À cadrer | Consulter et réutiliser les publications publiques AleaQuant dans un format textuel structuré, facilement exploitable par les IA, documentalistes et scripts. | Une représentation Markdown et, si utile, un export JSON des faits/claims publiables sont dérivés du même contenu approuvé que le HTML. URL canonique, jeu/régime éventuel, dates, version, sources et limites d'interprétation sont conservés. Les figures ont légendes et descriptions textuelles ; les données associées sont référencées quand elles sont publiables. Aucun brouillon ni contenu privé n'est exposé. Une correction met à jour les représentations ensemble ; cohérence et budget d'assets sont vérifiés. |

| PB-016 | P1 | Partiel local | Lire les contenus avec une progression des notions de base vers les sujets experts. | Inventaire des notions sur tout le site, prérequis versionnés transitifs, définitions accessibles et publiées avant les contenus dépendants ; glossaire direct, articles via pipeline éditorial ; blocage vérifié d'une publication dont un prérequis manque. Scout guidé par l'inventaire : repérer les chaînes bloquées et proposer un glossaire ou un article selon le besoin et l'intérêt éditorial ; prompt v1.3 livré, raccordement et qualification dans TD-SCOUT-001 canonique. Premier lot : catalogue des portefeuilles, 43 notions observées et 46 définitions locales. Atlas général et publication publique restent à faire. |
| PB-017 | P1 | À reprendre | Bénéficier d'une rédaction et d'une relecture adaptées au niveau d'expertise de l'article. | Profils initiation/approfondissement/expert paramétrant modèle, prompt, effort de réflexion et spécialistes selon compétences qualifiées ; choix traçable et limites de calcul explicites. Contrôles de preuves, dépendances et approbation humaine identiques à tous les niveaux. Principe cadré ; routage non implémenté, reprise demandée dès que possible. Voir TD-EDIT-001. |
| PB-018 | P1 | Prototype apprécié, style validé ; intégration à concevoir | Reconnaître d'un coup d'œil la dispersion ou la concentration d'un portefeuille, puis explorer les branches de l'Atlas et ouvrir ses grilles dans le prompteur. | Matrice de présences avec boules de loto texturées, réseau des numéros communs et sélection reliée au prompteur ; parcours en dossiers virtuels et vignettes conservant contexte, versions et filiation. Lecture vérifiée sur 20 et 30 grilles, mobile et clavier, avec définitions et légendes accessibles. Voir le cadrage ci-dessous ; prolonge PB-005 et PB-016. |
| PB-019 | P2 | À cadrer — après la v0 | Construire et comparer ses propres portefeuilles à partir d'un pool choisi et fixé, avec des objectifs et limites explicites. | Atelier personnalisé raccordé au pipeline existant : pool numéros/étoiles, nombre de grilles, budget et contraintes ; plusieurs candidats, validations, comparaisons RANDOM pertinentes, évaluations bornées, visualisations et conservation privée avec versions et prompteur. Des portefeuilles de référence complets, leurs vraies grilles et leurs explications restent gratuits dans l'Atlas. La personnalisation ne constitue aucune promesse prédictive. Voir TD-ATELIER-001. |
| PB-020 | P2 | À cadrer — après la v0 | Souscrire au service personnalisé et gérer son abonnement et ses paiements depuis son compte. | Offre, tarifs, périodicité et quotas définis ; parcours de souscription, paiement, renouvellement, changement d'offre et résiliation compréhensible. État de l'abonnement et droits d'accès cohérents avec les événements de paiement ; factures/reçus, échecs et remboursements traités selon les règles retenues. L'Atlas public de référence reste gratuit. Fournisseur et tarification à choisir ; voir TD-SUB-001. |

## Cadrage initial de PB-019 / PB-020 — atelier et souscription

Décision de Chris le 11 octobre : conserver des exemples complets et gratuits
dans l'Atlas, puis proposer un atelier personnalisé avec souscription et paiement.
La valeur du service porte sur la construction sous contraintes, les diagnostics,
la comparaison, les visualisations et la gestion des portefeuilles. Le choix des
numéros par l'utilisateur personnalise le domaine de construction ; il ne rend
pas ces numéros plus susceptibles de sortir au prochain tirage.

Le pool est explicite et figé pour une construction ; toute modification crée
une nouvelle configuration et conserve les résultats antérieurs. Réutiliser
les profils, opérateurs, validations et évaluations du pipeline de recherche,
avec identités, graines, provenance et limites de calcul. Les résultats privés
de l'utilisateur sont distincts des références scientifiques publiques de l'Atlas.

Définir les prestations incluses, les quotas, la consommation de calcul en cas
d'échec ou d'interruption et l'accès aux résultats après résiliation. La gestion
des abonnements payants est distincte de l'inscription à la newsletter PB-013.
La qualification doit relier paiement, droits et demandes de calcul, sans double
facturation ni accès indu. Aucun fournisseur, tarif, compte marchand ou paiement
réel n'est configuré par cette inscription. Ces fonctions ne bloquent pas la v0
manuelle ; elles seront cadrées et qualifiées avant ouverture du service.

## Cadrage initial de PB-018 — la vitrine visuelle de l'Atlas

Direction retenue par Chris le 10 octobre 2026 après consultation de l'aperçu
interactif : la matrice et le réseau complètent l'Atlas et son prompteur. La
préférence graphique est de représenter les présences par des **boules de loto
texturées**, avec des numéros lisibles. L'intégration au site reste à réaliser.

**Style validé le 10 octobre 2026** : boules bleues satinées, grain fin, léger
relief et chiffres sombres sur une pastille claire. Le bleu pourra s'intensifier
avec la fréquence du numéro. L'[image validée](references/atlas-textured-lottery-balls-v1.png)
est conservée dans le dépôt avec sa [fiche de référence v1.0](references/atlas-textured-lottery-balls-v1.md).
Cette validation porte sur le rendu proposé ; sa lisibilité dans la matrice
dense et son intégration restent à vérifier.

Livraison envisagée en deux étapes :

1. **Vue d'ensemble du portefeuille** : conserver la matrice grilles × numéros,
   les étoiles séparées et le réseau de liens selon les numéros communs. Les
   textures habillent les présences ; elles préservent l'échelle de fréquence,
   le contraste et la distinction entre absence et valeur hors pool. Une ligne
   ou un point sélectionné ouvre la grille correspondante dans le prompteur.
   Prévoir une lecture agrandie lorsque la densité rend les boules trop petites.
2. **Explorateur de l'Atlas** : navigation inspirée du Finder, avec dossiers
   virtuels, vignettes de portefeuilles, fil d'Ariane et retour au contexte.
   Les regroupements suivent les études, exécutions, générations et portefeuilles
   enregistrés. Les liens vers parents et descendants permettent de parcourir
   les branches ; un croisement conserve l'accès à ses deux parents, même si
   l'écran utilise une présentation en dossiers.

Les vignettes représentent les grilles réelles et gardent leur identité de
contenu et leur contexte. Les évaluations restent rattachées au portefeuille.
La couleur de fréquence ne représente pas la couverture des paires ou triplets,
qui demande une couche distincte. Les pools et périmètres de comparaison restent
visibles ; les positions du réseau en cercle ne mesurent aucune distance.
Les notions et leurs liens suivent PB-016 et la règle documentaire du site.

Référence à conserver pour la réalisation :

- [Aperçu autonome consulté](</Users/chris/Documents/Codex/2026-10-09/peu/outputs/geometrie-portefeuilles.html>).
- [Source interactive](</Users/chris/Documents/Codex/2026-10-09/peu/work/geometrie-portefeuilles.html>).

Cet aperçu présente quatre portefeuilles réels de **20 grilles**. La variante
texturée, l'intégration au prompteur, le parcours en dossiers et la qualification
sur **30 grilles** sont des travaux à venir. La recette devra vérifier les liens
et le retour de navigation, la fidélité aux grilles, les légendes et la lecture
sur ordinateur, mobile et clavier avant publication.

## Cadrage initial de PB-015 — contenus pour les outils et les IA

Idée retenue le 3 octobre 2026, inspirée de la
[documentation Apple Metal en Markdown](https://developer.apple.com/documentation/metal/generating-and-loading-a-metal-library-symbol-file.md).
L'objectif est un accès simple au contenu validé, en complément du HTML accessible
et sémantique. Le Markdown facilite l'extraction ; il ne garantit ni une meilleure
indexation ni la citation du site par une IA.

- Commencer par quelques articles de fond, les définitions de métriques et les
  notes de méthode. Garder la séparation entre prose éditoriale et registre des claims.
- Conserver les preuves et leur portée : une hypothèse, une simulation et un calcul
  exhaustif doivent rester distinguables après export, y compris hors de la page web.
- Proposer un lien de découverte depuis la page HTML et un petit index des contenus
  exportables. Le choix entre URL `.md`, route dédiée et négociation HTTP reste ouvert.
- Produire les formats depuis une source commune et la même révision approuvée ;
  ne pas réécrire les conclusions par LLM pour fabriquer la version destinée aux IA.
- Une illustration scientifique nécessite une description et, si disponible, une
  table de valeurs ou une référence au jeu de données ; une image décorative ne
  devient pas une preuve. Les captures techniques doivent être expurgées de secrets.
- Chiffrer l'impact avant extension aux archives : ne pas doubler les milliers de
  fichiers statiques de tirages. Étudier les routes à la demande dans le cadre de
  [SCALING.md](SCALING.md). Aucun export nouveau n'est déployé à ce stade.

## PB-021 — profils éditoriaux par jeu

Priorité P1 · décision du 11 octobre 2026 · à formaliser.
Chaque agent reçoit un profil de jeu versionné : identifiant du jeu, régime daté,
composants réels (numéros, étoiles, Chance), domaine et taille, vocabulaire,
métriques disponibles, règles de comparaison historique, dépendances pédagogiques
et limites d’interprétation. La constitution, le ton et les contrôles restent communs.
Ne pas transformer un tirage Keno en grille jouée ni sa probabilité en chance de gain.
Ce profil est distinct du niveau d’expertise, du modèle, de l’effort et du mode
natif Codex/API. Rédaction native ici demandée ; même source de prompts dans les
modes. Premiers correctifs multijeux livrés pour le lot v0 ; contrat explicite,
rejet des incompatibilités et qualification représentative restent TD-EDIT-GAME-001
canonique. Rattachement PB-017 ; aucune clôture générale du routage.

## Historique

- v0.16 (2026-10-11) — PB-021 profils de jeu communs à tous les agents et
  modes ; séparation jeu, expertise et moyens de rédaction.

- v0.15 (2026-10-11) — ajoute PB-019 atelier personnalisé et PB-020 souscription/
  paiement, avec Atlas de référence gratuit ; réalisation et qualification
  suivies par TD-ATELIER-001 et TD-SUB-001, après la v0.

- v0.14 (2026-10-11) — PB-016 inclut le Scout documentaire guidé par inventaire
  et dépendances : glossaire si suffisant, article pour explication utile ;
  prompt cadré, raccordement et qualification dans TD-SCOUT-001 canonique.

- v0.13 (2026-10-10) — PB-010 devient partiel : collecte gratuite RSS/arXiv
  persistante livrée ; recherche scientifique/éditoriale complète, curation et
  suivi console restent à réaliser. OPS-010 et dette canonique TD-WATCH-001/002.
- v0.12 (2026-10-10) — structure courte de l'accueil retenue pour la v0 manuelle ;
  références d'articles consultables, revue par IDs et actions de lancement dans
  `V0-MANUAL-RELEASE.md` ; aucune publication nouvelle.
- v0.11 (2026-10-10) — consigne le style de boules texturées validé pour PB-018 ;
  conserve l'image, sa provenance et les critères de réalisation dans le dépôt.
- v0.10 (2026-10-10) — ajoute PB-018 : vitrine visuelle de l'Atlas, boules de loto
  texturées dans la matrice, liens vers le prompteur puis exploration par dossiers
  et vignettes ; conserve l'aperçu apprécié comme référence, sans intégration au site.
- v0.2 (2026-10-02) — ajoute PB-008 pour le registre et les mini notes de version
  du modèle AleaQuant ; priorités proposées à confirmer au fil des livraisons.
- v0.3 (2026-10-02) — ajoute PB-009 pour le précontrôle SEO éditorial et sa checklist
  vivante, séparée des règles stables de style.
- v0.4 (2026-10-02) — ajoute PB-010 pour la recherche web sourcée du Scout et son
  adaptateur de recherche configurable.
- v0.5 (2026-10-02) — ajoute PB-011 pour le tableau de suivi et le brief opérationnel
  privé quotidien, PB-012 pour le flux RSS des publications, et PB-013 pour la
  newsletter éditoriale hebdomadaire avec inscription volontaire.

- v0.6 (2026-10-02) — ajoute PB-014 : administration des calculs, complément
  actionnable de la vue de suivi PB-011. Module demandé, pas encore implémenté.

- v0.7 (2026-10-02) — précise PB-014 : même outil que Review, six onglets cibles,
  catalogue des tâches récurrentes et livraison progressive.
- v0.8 (2026-10-03) — ajoute PB-015 : représentations textuelles des publications
  pour outils et IA, depuis la même source approuvée ; idée produit à cadrer,
  distincte de la dette technique et du sujet éditorial sur les expériences GPU.
