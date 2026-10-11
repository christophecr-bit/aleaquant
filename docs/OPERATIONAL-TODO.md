# TODO opérationnelle AleaQuant

Auteur : AleaQuant · v0.8 · 11 octobre 2026

## Recette / production — 3 octobre 2026

- [x] Recette Cloudflare isolée et protégée, snapshot SHA, noindex, contrôle humain possible.
- [ ] Livrer directement en production le lot validé en recette, puis automatiser
  ce parcours dans la CI. Aucun staging distinct à créer.
- Procédure : [RECETTE.md](RECETTE.md) ; architecture : [CI-STAGING-PRODUCTION.md](CI-STAGING-PRODUCTION.md).

Cette liste contient les actions concrètes de mise en service, vérification et
coordination. Elle ne définit pas les fonctions produit (`PRODUCT-BACKLOG.md`),
ne remplace pas les risques techniques (`TECHNICAL-DEBT.md`) et ne sert pas à
stocker des décisions d'architecture ou des sujets éditoriaux (`TASKS.md`). Les
actions répétitives peuvent être cochées à chaque occurrence dans le journal
d'exploitation plutôt que supprimées du processus.

| ID | Fréquence / statut | Action | Résultat à consigner | Lié à |
|---|---|---|---|---|
| OPS-010 | Quotidien 09 h 05 — installé ; prochain calendrier à observer | Consulter le statut de veille RSS/arXiv, contrôler les cinq flux, les erreurs et les fenêtres potentiellement manquées ; qualifier la reprise après arrêt du Mac sans lancement de rédaction implicite. | Dernière collecte, nouveaux éléments/versions, HTTP/cache, limites, erreurs et éventuelles interruptions. Deux runs réels qualifiés le 10 octobre ; code 0. Guide canonique `../../aleaquant-editorial-agents/docs/RESEARCH-WATCH.md` ; TD-WATCH-001/002 restent ouverts. | PB-010, PB-011 |
| OPS-008 | V0 manuelle — contenu à valider | Faire relire l'accueil court par IDs de blocs, choisir les destinations définitives, préparer les prérequis et un lot complet préservant la production, faire valider la recette puis livrer le lot autorisé avec Codex. | Manifeste exact de l'accueil, IDs et SHA des articles retenus, validation humaine, contrôle documentaire, empreintes du lot, version Worker et contrôles publics. Guide : `V0-MANUAL-RELEASE.md`. | PB-001, PB-003, PB-016 |
| OPS-009 | À chaque correction rédactionnelle | Résoudre l'article par son `article_id`, préserver l'édition relue, préparer une nouvelle version via le circuit éditorial canonique, recontrôler les claims et présenter le nouveau SHA à l'humain avant remplacement. | Référence stable, anciennes/nouvelles versions, demande de correction, contrôles et décision humaine. L'archivage des éditions est à qualifier : TD-EDIT-002. | PB-003 |
| OPS-007 | À chaque contenu ou publication | Déclarer les notions et leurs prérequis versionnés ; incrémenter le glossaire directement, envoyer les articles au pipeline éditorial ; vérifier la fermeture transitive des dépendances publiées. | Inventaire, versions, preuves publiques et refus éventuel de publication ; distinguer local, recette et public. | PB-016 |
| OPS-001 | À chaque rafraîchissement | Vérifier le résultat du pipeline local de récupération et de calcul pour les trois jeux ; contrôler les logs, les lois utilisées, les nouvelles fiches et les erreurs de source. | Date, jeux/régimes traités, nombres de résultats/faits, erreurs ou rattrapage requis. | PB-002 |
| OPS-002 | À chaque lot éditorial | Examiner les brouillons dans la console privée ; approuver le SHA exact, ou refuser/retourner avec une remarque exploitable. | Décision, reviewer, empreinte et commentaire associés au dossier. | PB-003, PB-004 |
| OPS-003 | À chaque publication | Vérifier les contrôles locaux, intégrer seulement les articles approuvés, déployer le Worker, vérifier les URL publiques puis pousser le commit Git. | URL vérifiée, version Worker, commit et éventuels écarts. | PB-001, PB-002, PB-003 |
| OPS-004 | Après redémarrage ou mise à jour macOS | Vérifier la reprise du serveur de revue et du tunnel Cloudflare ; tester `review.aleaquant.org` depuis une session Access et confirmer que le service local reste lié à `127.0.0.1`. | État des LaunchAgents, accès externe et état de veille/réseau. | PB-004 |
| OPS-005 | Prochaine suite complète | Réconcilier le test du profil Keno qui attend 332 observations alors que les données locales en contiennent 333, puis lancer toute la suite avec l'environnement Python du dépôt. | Cause comprise, assertion/fixture mise à jour si justifiée, suite complète documentée. | PB-002 |
| OPS-006 | À chaque évolution du modèle | Avant déploiement d'une nouvelle métrique, claim de méthode, règle/régime, moteur ou correction de données, compléter le registre canonique, rattacher les preuves et empreintes des dépôts, faire relire le résumé public puis publier la mini note avec la mise à jour correspondante. | Version du modèle, portée jeux/régimes, données recalculées, validation et URL de note. | PB-008 |

## Historique

- v0.7 (2026-10-10) — ajoute OPS-010 pour la veille quotidienne gratuite et sa
  qualification opérationnelle ; la publication et les appels LLM restent séparés.
- v0.6 (2026-10-10) — ajoute OPS-008 pour le lancement manuel de la v0 et OPS-009
  pour les corrections rédactionnelles par référence stable, sans approbation automatique.
- v0.4 (2026-10-03) — clarification : recette validée → production directe ;
  retrait de la tâche de création d'un staging distinct.

- v0.2 (2026-10-02) — ajoute le contrôle/passage en publication des mini notes de
  version du modèle AleaQuant.

## Lot traçabilité — 2 octobre 2026

- [x] Spécifier et réaliser Sources et méthode, rendu dépliable et SHA associé.
- [x] Corriger le pipeline C2/C5 et les fuites de consignes ; tests témoins permanents.
- [x] Distinguer provenance directe/batch, sans falsifier les anciens dossiers.
- [x] Tester la transmission des sommes par dizaine lorsqu'elles sont disponibles.
- [ ] Relire et décider du nouveau témoin EM-26078 avant toute publication.
- [x] Recalcul global exécuté et comparé ; exception de bascule EM-2011053 documentée ci-dessous.

## Validation du lot recalcul-20261002

- [x] Recalculer trois fiches sur régimes actuel/ancien et comparer tous les anciens faits.
- [x] Vérifier que les sommes par dizaine arrivent au LLM et dans les preuves citées.
- [x] Exercer l'entrée LangGraph : deux prêts à relire, un bloqué légitimement.
- [ ] Relire EM-26078 et EM-2004010 dans la file privée ; aucune approbation automatique.
- [ ] Reprendre le texte EM-26077, sans changer ses faits ni les critères des puces.

## Rattrapage global des faits — 2 octobre 2026

- [x] Recalculer et comparer les 29 124 fiches des trois jeux.
- [x] Installer 29 120 mises à jour et préserver les 3 témoins déjà conformes.
- [ ] Revalider l'article EM-2011053 avant de remplacer son unique fiche protégée.
- [ ] Étendre la conservation des snapshots approuvés pour les futures évolutions.
Rapport : RECALCUL-FAITS-TROIS-JEUX-20261002.md. Aucun nouvel article ni déploiement.

## Publication du recalcul — 2 octobre 2026

- [x] Reconstruire les 9 991 pages et rejouer les tests web : 129 + 28 sous-tests.
- [x] Publier le snapshot validé sur les deux domaines du Worker aleaquant.
- [x] Vérifier les trois jeux, les histogrammes et l’article approuvé inchangé.
- [x] Consigner version Worker, empreintes et contrôles HTTP dans DEPLOYMENTS.md.
- [ ] Revalider séparément l’article EM-2011053 avant bascule de sa nouvelle fiche.

## Préparer l’exploitation depuis la console — PB-014

- [x] Cadrer un outil privé unique avec Review et consigner les tâches récurrentes
  dans [l’architecture commune](../../aleaquant-editorial-agents/docs/ADMIN-CONSOLE-ARCHITECTURE.md).
- [ ] Qualifier chaque action existante : paramètres, entrées/sorties, verrou,
  idempotence, coût, reprise et effets sur les approbations.
- [ ] Valider un parcours depuis téléphone : état des trois jeux → recalcul ciblé →
  comparaison → rapport, sans terminal et sans publication implicite.
- [ ] Vérifier que tous les services/onglets affichent leur état réel et la date du
  dernier contrôle ; signaler les capacités non raccordées.

## Contrôle après redémarrage — 2 octobre 2026

- [x] Vérifier Review, tunnel, Access, écoute SSH et planification de collecte.
- [x] Réparer les anciens chemins de collecte ; préflight et 9 tests conformes.
- [x] Restaurer une preview unique sur 4173 via LaunchAgent utilisateur.
- [ ] Contrôler le prochain refresh planifié et une connexion SSH externe complète.
- [ ] Clarifier le rôle de l’ancien cloudflared système avant nettoyage.

Rapport : SERVICES-POST-RESTART-20261002.md. Aucun déploiement ou calcul massif.

## Lot de lancement — 11 octobre 2026

- [x] Préparer les trois articles des derniers tirages affichés (EM-26081,
  LO-20261007, KE-26372), contrôles et intake READY_FOR_HUMAN, sans approbation.
- [ ] Relire et valider les SHA du lot : dépôt canonique
  `runs/v0-latest-draws/2026-10-11-v1/manifest.json`.
- [ ] Qualifier les dépendances publiées et actualiser la fraîcheur des tirages
  avant intégration, recette et lancement.
- [ ] Relire le rattrapage depuis le 1 octobre : 12 articles natifs Codex, Luna
  medium EM/Loto, high Keno, prompts de production communs, sans API externe.

Lot natif préparé le 11 octobre : les douze articles de rattrapage et les trois
derniers tirages locaux sont en attente dans la console 8787. Leur préparation
ne vaut pas validation humaine ni publication ; freshness et prérequis restent requis.
