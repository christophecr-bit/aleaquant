# Tâches de cadrage et de coordination — AleaQuant

Auteur : AleaQuant · v0.1 · 1er octobre 2026

Ce registre suit uniquement les explorations et arbitrages qui doivent produire
une information, une comparaison ou une décision. Il ne sert pas de TODO
opérationnelle. Il ne duplique ni les fonctions de
[`ROADMAP.md`](ROADMAP.md), ni les composants à réaliser dans
[`TECHNICAL-DEBT.md`](TECHNICAL-DEBT.md), ni les décisions déjà actées dans les
documents d'architecture. Le classement des fonctions produit est dans
[`PRODUCT-BACKLOG.md`](PRODUCT-BACKLOG.md), les actions concrètes d'exploitation
dans [`OPERATIONAL-TODO.md`](OPERATIONAL-TODO.md). Lorsqu'une exploration débouche
sur un choix, celui-ci est consigné dans l'architecture concernée et la tâche est
clôturée ici.

| ID | Statut | Tâche | Livrable attendu |
|---|---|---|---|
| DISC-001 | À cadrer | Comparer les options de stockage distant gratuit ou à faible coût pour les données AleaQuant (archives, index, exports et sauvegardes). | Note datée séparant stockage objet, base de données et hébergement ; quotas gratuits, coûts après quota, appels/egress, sauvegarde/versionnement, confidentialité, compatibilité avec Workers et maintien des calculs sur le Mac ; recommandation « rester local » incluse si aucun besoin ne justifie une migration. |
| DISC-002 | À instruire après la revue mobile | Comparer le maintien du générateur actuel au portage de l'accueil vers Astro. | Décision d'architecture basée sur rendu mobile, temps de génération, nombre d'assets, compatibilité Worker et coût de maintenance ; aucun portage avant décision. |
| DISC-003 | Proposition formulée — validation à venir | Valider le périmètre MVP de la homepage, ses rubriques, le tri des contenus de démonstration et le nombre de cartes visibles par rubrique sur mobile et desktop. | Proposition de contenu et de hiérarchie dans [`SITE-EDITORIAL-ARCHITECTURE.md`](SITE-EDITORIAL-ARCHITECTURE.md) ; décision utilisateur, puis maquette actualisée et revue mobile. |

## Règle de suivi

Une tâche n'est close qu'avec son livrable ou sa décision et un lien vers celui-ci.
Les recherches de fournisseurs ne déclenchent aucun compte, achat, migration ou
déploiement à elles seules.
