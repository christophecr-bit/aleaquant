# Politique CI, recette et production AleaQuant

**Version :** 0.2 · **Date :** 2026-10-03 · **Auteur :** AleaQuant
**Statut :** architecture validée sur trois environnements ; recette déployée et protégée par Access, staging distinct et CI à réaliser.

## Décision retenue le 3 octobre 2026

Christophe demande **recette → staging distinct → production**. Chaque niveau
possède un Worker et une configuration propres ; aucun déploiement implicite
au niveau suivant.

| Niveau | Worker / domaine | Rôle | État |
|---|---|---|---|
| Recette | `aleaquant-recette` / `recette.aleaquant.org` | Valider le rendu, la maquette et les fonctionnalités sur un lot figé. | Déployé le 3 octobre ; Access vérifié. |
| Staging | `aleaquant-staging` / `staging.aleaquant.org` | Répéter la livraison du candidat validé en conditions proches de la production. | À créer séparément. |
| Production | `aleaquant` / `aleaquant.org` | Site publié. | Existant ; inchangé par la préparation recette. |

La recette est, et le futur staging devra être, protégé par Access, exclu de l'indexation,
sans adresse `workers.dev` ni URL de preview contournant cette protection.
`private.aleaquant.org` reste le tunnel SSH ; `review.aleaquant.org` reste la
console éditoriale sur le Mac. La recette sert des fichiers sur Cloudflare et
n'exige pas que le Mac soit allumé.

La mise en place recette utilise une configuration séparée
`wrangler.recette.jsonc`, jamais un remplacement de `wrangler.jsonc` production.
Procédure et paquet figé : [RECETTE.md](RECETTE.md). Pas de nouveau calcul de
faits ni de génération d'article pour préparer le paquet.

## Modèle Cloudflare

Wrangler permet des environnements nommés persistants, par exemple
`--env staging`; un environnement déploie un Worker distinct, généralement
`aleaquant-staging`. Les bindings, `vars`, routes et domaines doivent être
déclarés explicitement dans chaque environnement : ils ne sont pas hérités.
Cloudflare provisionne un certificat pour chaque environnement publié ; les
noms d’environnement ne doivent donc pas contenir d’information secrète.

Les Previews Cloudflare sont destinés aux branches et pull requests ; les
environnements Wrangler conviennent mieux à une recette permanente. Les Version
URLs permettent de contrôler une version téléversée avant de la déployer. Une
version capture code, assets, bindings et compatibilité, mais pas l’état modifié
des bases et stockages associés. Aujourd’hui le site est principalement
statique et le déploiement envoie `dist/` ; la séparation des données devra être
réexaminée si un service avec état est ajouté.

## Flux de livraison

```mermaid
flowchart LR
  A[Sources et contrôles] --> B[Lot figé avec manifeste SHA]
  B --> C[Recette privée]
  C --> D[Validation humaine du rendu et des fonctions]
  D --> E[Staging privé distinct]
  E --> F[Vérifications de livraison]
  F --> G[Approbation de production]
  G --> H[Production]
```

Le flux CI cible est encore à construire. La première recette est une livraison
manuelle explicite et isolée. Un lot de travail peut contenir des changements
locaux non committés : le manifeste l'indique, et **ne vaut pas candidat de
production validé**. Pour promouvoir, figer et versionner les sources approuvées.
Les fichiers de contenu doivent garder leurs SHA entre niveaux ; les surcharges
propres à l'environnement (`_headers`, `robots.txt`, domaine) sont identifiées
séparément. Ne jamais promouvoir par mégarde un `Disallow: /` en production.

## Règles CI cibles et publication

1. Toute modification passe par une branche ou une PR et des contrôles locaux/CI.
   Aucun `wrangler deploy` lancé depuis un poste n’est requis pour le flux normal.
2. La CI enregistre le SHA Git, les versions d’outils et le manifeste des assets
   (`dist/`) dans les journaux de livraison. Données générées, rapports et
   secrets ne sont pas embarqués par défaut.
3. Un déploiement sur recette ne modifie jamais le Worker de production. La
   recette est protégée par Cloudflare Access et marquée `noindex` ; vérifier
   que le Worker ne divulgue pas de brouillons ou de données non destinés au
   public avant d’y envoyer l’intégralité de `dist/`.
4. La recette humaine porte sur un SHA précis. Si le commit change, la validation
   expire et la recette doit être rejouée.
5. Le passage en production exige une approbation explicite de l’environnement
   GitHub `production`. Promouvoir le même commit de contenu validé en recette puis staging, avec
   ses seules surcharges d’environnement tracées ; reconstruire à partir
   d’entrées non figées invalide cette équivalence.
6. Après déploiement, vérifier HTTP 200, HTTPS, pages représentatives des jeux,
   histogrammes et fichiers statiques, puis consigner version Worker, SHA,
   résultat et heure dans `docs/DEPLOYMENTS.md`.
7. En cas d’échec fonctionnel, restaurer le déploiement Worker précédent avec
   Wrangler ou le tableau de bord. Le rollback de code n’annule pas des changements
   d’état dans D1/R2/KV : les futures migrations de données auront une procédure
   dédiée.
8. Les secrets CI restent dans les secrets d’environnement GitHub/Cloudflare ;
   ne jamais les committer ni les inclure dans les logs. Les identifiants de
   production ne sont accessibles qu’au job production.

## Validation éditoriale et recette technique

Ces validations sont distinctes. La recette technique vérifie que le site,
les routes et les assets fonctionnent. L’approbation éditoriale vérifie le
contenu : l’article garde son approbation liée au SHA-256 exact du brouillon.
Une CI verte ne vaut pas approbation éditoriale et une approbation d’article ne
vaut pas validation du déploiement.

## Clés et identités de service

Ne pas réutiliser le jeton du tunnel `cloudflared` comme clé de déploiement ni
comme authentification de l’interface de recette. Ce jeton autorise uniquement
le connecteur installé sur le Mac à établir le tunnel Cloudflare ; il n’est pas
une clé privée SSH et n’accorde pas, à lui seul, l’accès à l’application.

| Usage | Identité recommandée | Stockage et portée |
|---|---|---|
| Connexion humaine à la recette | Identité interactive derrière Cloudflare Access (Google ou code e-mail) | Politique Access limitée au propriétaire ; MFA si disponible |
| Déploiement CI vers Workers | API Token Cloudflare dédié au projet avec droit Workers Scripts Edit, limité au compte requis | Secret de l’environnement GitHub `production`; clé distincte pour recette si nécessaire |
| Tunnel vers le Mac | Jeton propre au tunnel Cloudflare | Conservé seulement sur le Mac, fichier LaunchAgent lisible par son compte ; rotation en cas d’exposition |
| Approbation de mise en production | Approbateur de l’environnement protégé GitHub | Approbation associée au SHA validé |

Si « clé privée de service » désigne un Service Token Cloudflare Access, celui-ci
sert à l’authentification machine-à-machine vers une application protégée. Il ne
remplace ni le jeton du tunnel, ni l’API Token de déploiement, ni la connexion
interactive requise pour la revue humaine. Pour la recette consultée par Chris,
préférer une politique Access avec identité personnelle plutôt que de distribuer
un Service Token au navigateur.

## Mise en place par étapes

1. Créer l’application Cloudflare Access de `recette.aleaquant.org` et son
   Worker `aleaquant-recette` sans modifier la production.
2. Préparer la recette avec `wrangler.recette.jsonc` et un snapshot isolé.
   Créer ensuite le staging séparément ; chaque configuration déclare son nom,
   domaine, assets et bindings sans hériter des routes de production.
3. Créer une CI GitHub qui exécute les contrôles déjà disponibles et déploie
   recette puis staging seulement après les validations requises. Configurer `production` comme environnement
   protégé avec approbation humaine.
4. Tester une livraison de bout en bout et le rollback avant de désactiver le
   déploiement manuel historique.
5. Ajouter ensuite, si utile, des Workers Previews par PR, avec nettoyage des
   previews fermées et Access si elles utilisent un domaine personnalisé.

## État actuel et prérequis

- Production : Worker `aleaquant`, domaine personnalisé `aleaquant.org`,
  `workers.dev` activé.
- La maquette `/maquette/` existe encore sur le Worker de production ; sa copie
  en recette permet désormais de valider un lot séparément. Consulter
  [RECETTE.md](RECETTE.md) pour le statut de la première livraison.
- Aucun workflow GitHub Actions de livraison n’a été trouvé dans le dépôt au
  moment de cette proposition.
- Avant activation CI : rétablir l’accès GitHub du poste, vérifier que la branche
  distante contient les commits locaux à livrer, et choisir les contrôles
  déterministes obligatoires. Ne pas lancer un push forcé pour contourner l’écart.
- Wrangler observé le 3 octobre : 4.147.0. Le projet ne dispose pas encore
  d’une dépendance Wrangler locale figée ; épingler sa version CI avant automatisation.

## Références officielles

- [Environnements Wrangler](https://developers.cloudflare.com/workers/wrangler/environments/)
- [Configuration Wrangler](https://developers.cloudflare.com/workers/wrangler/configuration/)
- [Cloudflare Workers Previews](https://developers.cloudflare.com/workers/previews/)
- [Version URLs](https://developers.cloudflare.com/workers/versions-and-deployments/version-urls/)
- [Versions et déploiements](https://developers.cloudflare.com/workers/versions-and-deployments/)
- [Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)
- [Déploiements progressifs](https://developers.cloudflare.com/workers/versions-and-deployments/gradual-deployments/)

Historique : v0.1 — proposition initiale ; v0.2 — trois niveaux distincts
confirmés par Christophe, recette séparée et promotion du contenu tracée.
