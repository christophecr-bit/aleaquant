# Backlog produit AleaQuant

Auteur : AleaQuant · v0.7 · 2 octobre 2026

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
| PB-001 | P0 | À cadrer | Accueil éditorial organisé en rubriques et cartes compréhensibles, avec les derniers tirages mis en avant. | Hiérarchie MVP validée, exemples triés et maquette responsive alignée sur `SITE-EDITORIAL-ARCHITECTURE.md`. |
| PB-002 | P0 | En cours | Consulter EuroMillions, Loto et Keno depuis une URL stable avec résultat, faits et visualisations cohérents. | Les trois jeux sont accessibles ; les deux régimes Keno sont distingués ; l'historique Keno ne crée pas des milliers de pages statiques. |
| PB-003 | P1 | Partiel | Lire une analyse éditoriale attachée à un tirage et naviguer entre l'article et sa page de résultats. | Article approuvé, rubrique et identité jeu/date affichées, claims et preuves contrôlés, intégration locale vérifiable. |
| PB-004 | P1 | Prototype | Relire sur ordinateur ou téléphone, approuver, refuser avec remarque et corriger une publication sans perdre les versions précédentes. | Console privée reliée au flux de publication rubricée, avec nouvelle empreinte après correction et approbation explicite avant intégration. |
| PB-005 | P1 | À qualifier | Explorer des familles de portefeuilles et comprendre leurs recouvrements, couvertures et limites. | Cohortes Loto et références EuroMillions/Keno accompagnées de leur protocole, provenance et référence RANDOM à budget égal. |
| PB-006 | P2 | Recherche cadrée | Comprendre quelques garanties conditionnelles exactes sur des pools et des rangs. | Cas pédagogiques calculés, certifiés indépendamment et présentés avec bornes et limites ; aucune promesse prédictive. |
| PB-007 | P2 | À instruire | Explorer résultats et faits historiques en tableau et les réutiliser dans ses propres analyses. | Filtres, pagination et exports CSV/JSON documentés avec schéma, régime, provenance et version des calculs. |
| PB-008 | P0 | À préparer pour le MVP | Comprendre ce qui a changé dans le modèle AleaQuant et si cela modifie les fiches publiées. | Registre versionné couvrant métriques, claims de méthode, règles/régimes, moteurs et corrections ; mini note lisible, jeux concernés, compatibilité, validation et plage recalculée publiés après revue humaine. |
| PB-009 | P1 | À cadrer | Produire des articles lisibles, bien structurés et techniquement compréhensibles par les moteurs de recherche. | Avant une campagne de rédaction/publication, la checklist Google Search Central est revue et datée ; chaque publication possède des titres et métadonnées adaptés, une hiérarchie de titres sémantique, des rubriques/tags contrôlés et un statut d'indexation cohérent avec sa valeur éditoriale. Les règles SEO ne peuvent modifier ni les faits ni les conclusions scientifiques. |
| PB-010 | P1 | À concevoir | Repérer des sujets éditoriaux à partir d'une veille web vérifiable, avec un angle AleaQuant et des preuves à collecter. | Le Scout reçoit un dossier de recherche issu de plusieurs requêtes, de sources primaires/fiables ouvertes et datées, avec citations, contrepoints et séparation explicite entre faits, interprétations et hypothèses. Aucun résultat de recherche n'est pris pour une preuve scientifique sans vérification par l'Evidence Planner. Le fournisseur de recherche est configurable et remplaçable ; tests en mode simulé. |
| PB-011 | P1 | À cadrer | Suivre depuis la console privée l'état des opérations AleaQuant et recevoir chaque matin un courriel personnel des changements, retards et points à traiter. | Une vue « Suivi » présente la fraîcheur et le dernier succès de chaque pipeline de tirages, les retards par jeu, l'état des faits/pages/déploiements, la santé des flux de veille, les recherches et leur coût si disponible, ainsi que les articles par étape jusqu'à la file d'approbation. Un digest déterministe, daté, idempotent et consultable dans la console est envoyé chaque matin à l'adresse privée configurée ; les métriques de fréquentation et d'exécution Cloudflare indiquent source, période et fraîcheur. Le fournisseur d'envoi et le comportement quand le Mac dort (rattrapage au réveil ou agrégat cloud limité) sont décidés ; les secrets restent côté serveur, les échecs sont visibles et relançables. Aucune publication ou action automatique n'est déclenchée. |
| PB-012 | P1 | À cadrer | S'abonner aux nouvelles publications AleaQuant dans un lecteur de flux RSS. | Un flux public valide recense les publications réellement publiées, avec URL canonique, titre, date, rubrique et résumé ; aucun brouillon ou contenu privé n'y apparaît. Le flux est vérifié avec un lecteur RSS et les pages restent accessibles sans abonnement. |
| PB-013 | P2 | À cadrer | Recevoir chaque semaine une sélection éditoriale AleaQuant, distincte du flux exhaustif des publications. | Une newsletter périodique assemble une sélection de contenus publiés et approuvés, avec liens canoniques et un court éditorial ; inscription explicite, désinscription fonctionnelle et gestion minimale des données d'abonnés sont vérifiées avant tout envoi. Le service d'envoi et l'archivage web sont choisis avant implémentation. |
| PB-014 | P1 | À concevoir | Piloter les opérations dans la même console privée que Review, avec plusieurs onglets, sans terminal ni intervention de Codex. | Navigation commune : Suivi, Tirages & calculs, Lots & agents, Review, Publication, Système ; journal transversal. Voir le [cadrage canonique](../../aleaquant-editorial-agents/docs/ADMIN-CONSOLE-ARCHITECTURE.md). Choisir le jeu, le régime, la période ou les tirages ; lancer la récupération, le recalcul des faits et la reconstruction des profils/pages via les outils existants ; suivre progression, logs, résultats et erreurs. Prévisualiser le périmètre et les conséquences avant un recalcul forcé, comparer les sorties avant installation et signaler les articles à revalider. Les tâches persistent après fermeture du navigateur ; reprise ou relance après interruption selon les capacités du batch. Les lancements concurrents avec launchd sont maîtrisés. Aucune publication automatique ; les snapshots approuvés restent protégés. |

## Historique

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
