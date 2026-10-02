# TODO opérationnelle AleaQuant

Auteur : AleaQuant · v0.2 · 2 octobre 2026

Cette liste contient les actions concrètes de mise en service, vérification et
coordination. Elle ne définit pas les fonctions produit (`PRODUCT-BACKLOG.md`),
ne remplace pas les risques techniques (`TECHNICAL-DEBT.md`) et ne sert pas à
stocker des décisions d'architecture ou des sujets éditoriaux (`TASKS.md`). Les
actions répétitives peuvent être cochées à chaque occurrence dans le journal
d'exploitation plutôt que supprimées du processus.

| ID | Fréquence / statut | Action | Résultat à consigner | Lié à |
|---|---|---|---|---|
| OPS-001 | À chaque rafraîchissement | Vérifier le résultat du pipeline local de récupération et de calcul pour les trois jeux ; contrôler les logs, les lois utilisées, les nouvelles fiches et les erreurs de source. | Date, jeux/régimes traités, nombres de résultats/faits, erreurs ou rattrapage requis. | PB-002 |
| OPS-002 | À chaque lot éditorial | Examiner les brouillons dans la console privée ; approuver le SHA exact, ou refuser/retourner avec une remarque exploitable. | Décision, reviewer, empreinte et commentaire associés au dossier. | PB-003, PB-004 |
| OPS-003 | À chaque publication | Vérifier les contrôles locaux, intégrer seulement les articles approuvés, déployer le Worker, vérifier les URL publiques puis pousser le commit Git. | URL vérifiée, version Worker, commit et éventuels écarts. | PB-001, PB-002, PB-003 |
| OPS-004 | Après redémarrage ou mise à jour macOS | Vérifier la reprise du serveur de revue et du tunnel Cloudflare ; tester `review.aleaquant.org` depuis une session Access et confirmer que le service local reste lié à `127.0.0.1`. | État des LaunchAgents, accès externe et état de veille/réseau. | PB-004 |
| OPS-005 | Prochaine suite complète | Réconcilier le test du profil Keno qui attend 332 observations alors que les données locales en contiennent 333, puis lancer toute la suite avec l'environnement Python du dépôt. | Cause comprise, assertion/fixture mise à jour si justifiée, suite complète documentée. | PB-002 |
| OPS-006 | À chaque évolution du modèle | Avant déploiement d'une nouvelle métrique, claim de méthode, règle/régime, moteur ou correction de données, compléter le registre canonique, rattacher les preuves et empreintes des dépôts, faire relire le résumé public puis publier la mini note avec la mise à jour correspondante. | Version du modèle, portée jeux/régimes, données recalculées, validation et URL de note. | PB-008 |

## Historique

- v0.2 (2026-10-02) — ajoute le contrôle/passage en publication des mini notes de
  version du modèle AleaQuant.

## Lot traçabilité — 2 octobre 2026

- [x] Spécifier et réaliser Sources et méthode, rendu dépliable et SHA associé.
- [x] Corriger le pipeline C2/C5 et les fuites de consignes ; tests témoins permanents.
- [x] Distinguer provenance directe/batch, sans falsifier les anciens dossiers.
- [x] Tester la transmission des sommes par dizaine lorsqu'elles sont disponibles.
- [ ] Relire et décider du nouveau témoin EM-26078 avant toute publication.
- [ ] Planifier le rattrapage explicite des anciennes fiches (voir dette technique).

## Validation du lot recalcul-20261002

- [x] Recalculer trois fiches sur régimes actuel/ancien et comparer tous les anciens faits.
- [x] Vérifier que les sommes par dizaine arrivent au LLM et dans les preuves citées.
- [x] Exercer l'entrée LangGraph : deux prêts à relire, un bloqué légitimement.
- [ ] Relire EM-26078 et EM-2004010 dans la file privée ; aucune approbation automatique.
- [ ] Reprendre le texte EM-26077, sans changer ses faits ni les critères des puces.
