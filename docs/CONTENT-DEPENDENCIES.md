# Dépendances documentaires — v1.0 · 10 octobre 2026

Le registre `configs/content-dependencies.json` distingue les définitions locales
des définitions publiées. Un article ou une page gérée reste bloqué tant qu’un
prérequis, ou l’un de ses prérequis transitifs, n’a pas de preuve de publication
publique pour la version et le contenu exacts demandés.

## Contrat versionné

Le schéma est `engine/content_dependencies.schema.json` ; les contrôles effectifs
sont dans `engine/content_dependencies.py`. Un nœud déclare `id`, `kind`
(`notion`, `article`, `page`), `version`, `content_sha256`, `target` (chemin asset
relatif et ancre), `requires` (références `{id, version}`), `related` (liens de
navigation) et `state` (`draft`, `local`, `published`). Seul `requires` forme le
graphe bloquant. Les cycles y sont refusés ; les liens voisins peuvent revenir
vers une autre notion sans créer de dépendance obligatoire.

Exemple de lecture : recouvrement → paire de grilles → grille → numéro et étoile.
Paires de numéros communes → paire de numéros et recouvrement. La page exige toute
la fermeture de ces dépendances, pas seulement une ancre de glossaire.

`notion_node` matérialise les records du glossaire et calcule leur empreinte sur
le contenu, la version, la cible et les relations. Le HTML conserve les attributs
`data-notion-id`, `data-notion-version`, `data-notion-sha256` sur l’entrée portant
son ancre. Une notion peut aussi viser une entrée réelle d’un article publié :
la définition, l’ancre et ces mêmes marqueurs restent exigés.

`page_node` lie une page au SHA de ses octets HTML. `article_node` lie un article
au SHA de son brouillon approuvé ; créer ce record ne donne aucune approbation
éditoriale. Un contenu déjà associé à une preuve de publication ne peut pas être
réécrit sous le même couple id/version. Une nouvelle version est nécessaire.
`update_nodes` conserve les versions et preuves précédentes.

## Preuve de publication

Un état `published` seul, un fichier dans `dist`, un export éditorial, une recette
privée ou un `wrangler --dry-run` ne suffisent pas. Une observation conserve :

- la réponse HTTP HTML publique dans un fichier relatif au dépôt et son SHA exact ;
- l’URL de production exacte, HTTP 200, une requête anonyme, l’heure avec fuseau ;
- l’identifiant du déploiement fourni par l’opérateur.

La publication lie le nœud, sa version et son SHA à cette observation. La garde
recalcule le SHA du corps conservé et vérifie l’ancre, les marqueurs et le texte de
la définition. La recette Access ne remplit pas ce contrat. L’identifiant de
déploiement est une référence opérateur ; ce mécanisme ne prétend pas attester
l’API Cloudflare ni signer cryptographiquement des fichiers du registre.
La preuve est datée : elle décrit la réponse observée, et doit être renouvelée
après modification, retrait ou rollback de la cible.
Avant un vrai déploiement, la garde reconfirme aussi la réponse actuelle par un
GET anonyme sans session ni cookie, avec un timeout de dix secondes. Elle regroupe
les références par URL et effectue au plus un GET par asset, puis refuse HTTP
404, une redirection/login, une origine différente ou un SHA modifié. Les imports
locaux et rapports locaux restent sans réseau. Une preuve conservée ne suffit
donc pas à publier si la cible a disparu depuis son observation.

Le sous-programme `observe` fait réellement le GET anonyme, borne la réponse à
5 Mo, refuse les redirections vers une autre URL et enregistre les preuves
seulement après vérification de toutes les entrées. Il n’a jamais été exécuté
contre le site dans ce jalon ; les preuves de tests restent dans des répertoires
temporaires, hors du registre réel.

## Garde branchée dans le circuit réel

Le dépôt canonique `../aleaquant-editorial-agents` appelle
`scripts/import_article.py` depuis `ReviewService.publish_to_site`. L’import
destiné à `dist/articles.json` vérifie les dépendances avant toute écriture du
journal et avant régénération de page. Le SHA du brouillon et l’approbation humaine
restent contrôlés. Les imports de transport vers un autre fichier restent des
opérations locales de test ; ils n’autorisent pas une publication.

`wrangler.jsonc` branche aussi `scripts/check_content_dependencies.py` comme
commande de build avant le déploiement standard. La garde vérifie toutes les
pages déclarées dans `managed_pages` présentes dans le lot et chaque article du
journal présent. Un article sans inventaire lié au SHA exact est refusé.
`--live-on-deploy` utilise `WRANGLER_COMMAND=deploy` pour réserver la
reconfirmation réseau au vrai déploiement ; il ne fait pas de GET pendant un
rapport local ou un développement Wrangler.

Pour un autre dossier d’assets, `scripts/deploy_site.py --assets <dossier>`
contrôle le véritable lot, sans réseau ni déploiement par défaut. Avec
`--execute`, il conserve les routes du Worker et génère une configuration dont
la garde vérifie ce même chemin absolu. Aucun déploiement n’a été lancé ici.
L’appel manuel de Wrangler avec une autre configuration ou `--no-bundle` peut
contourner une commande de build ; ce n’est pas un chemin de publication contrôlé.
La CI est encore absente et devra appeler cette garde explicitement avant upload.
[Documentation Cloudflare des builds](https://developers.cloudflare.com/workers/wrangler/custom-builds/).

## Amorçage et ordre d’un lot

Le glossaire direct peut être préparé seul, dans un dossier d’assets qui ne contient
ni page consommatrice gérée ni journal d’articles, pour préparer un rapport local
de dépendances. Ce dossier n’est pas un lot distant publiable : Wrangler remplace
le manifeste d’assets du Worker, donc un upload de ce sous-ensemble supprimerait
les autres pages. Le wrapper refuse `--execute` en l’absence de l’index du site.
Ce contrôle minimal ne prouve pas la complétude du lot ; la livraison réelle doit
partir d’un build de production complet et préservé, auquel les nouvelles
définitions sont ajoutées. L’inventaire des contenus publics historiques et leur
migration documentaire restent à réaliser (TD-DOC001) ; aucun article ancien
non enregistré n’est exempté de la garde.

Ses définitions locales doivent être cohérentes avec les marqueurs et le registre.
Le plan topologique range les
racines avant les notions composées, puis les pages et articles consommateurs ;
il ne crée aucune preuve de publication. Les racines incluses dans la même réponse
publique peuvent être enregistrées ensemble après ce premier déploiement.
Un prérequis situé dans une autre cible exige déjà sa propre preuve.
L’article ou l’Atlas ne devient publiable qu’après cette observation publique.
Si un lot consommateur contient aussi le glossaire, les définitions qu’il exige
doivent conserver leur version, SHA sémantique, marqueurs et texte. Le glossaire
peut gagner d’autres entrées sans bloquer les consommateurs déjà documentés.
Le GET final vérifie les définitions encore publiques avant le déploiement ; les
preuves HTTP du glossaire augmenté sont réactualisées après sa livraison.
Une nouvelle entrée ne débloque pas un nouveau consommateur pendant le même lot :
elle doit d’abord être publiée et observée. Retirer ou modifier une définition
encore requise bloque le lot.

```sh
python3 scripts/check_content_dependencies.py validate
python3 scripts/check_content_dependencies.py check page:portfolio-atlas --version 1.0
python3 scripts/check_content_dependencies.py plan page:portfolio-atlas@1.0
python3 scripts/deploy_site.py --assets /chemin/du/lot-glossaire
```

Après un déploiement explicitement autorisé et réussi, l’opérateur peut observer
la réponse publique :

```sh
python3 scripts/check_content_dependencies.py observe \
  --target-path comprendre/glossaire/index.html \
  --deployment-id IDENTIFIANT_DU_DEPLOIEMENT
```

Si plusieurs versions d’une notion sont conservées sur le même chemin, déclarer
explicitement les versions effectivement présentes par des options répétées
`--notion numero@1.1`, etc. La commande ne choisit jamais silencieusement une
« dernière version ». Elle garde les observations et preuves des versions
précédentes ; une version encore requise par des consommateurs doit rester
accessible à sa cible exacte, par exemple sous un chemin versionné.

## Inventaire et limites

L’inventaire des notions est explicite et revu humainement. Les dépendances
anticipées dans un sujet éditorial ne prouvent pas la complétude du brouillon
final : la relecture doit examiner ce brouillon exact, ses notions importantes
et leurs versions, puis enregistrer `article_node` pour son SHA approuvé.
Le système ne réalise aucune détection automatique exhaustive de la prose ou
du NLP. Une notion utilisée mais omise de l’inventaire reste une lacune de revue.

La garde porte sur les pages explicitement gérées et sur les articles importés ;
elle n’affirme pas avoir migré toutes les pages historiques du site. Les 46 notions
du premier glossaire et la page Atlas ont été enregistrées localement, avec zéro
observation et zéro publication. Les définitions ne sont donc pas déclarées
publiées, et le lot complet reste volontairement bloqué.

Historique v1.0 : registre versionné, graphe transitif, séparation `related`,
preuves exactes, import réel et hook de déploiement, lot documentaire distinct.
Tests : cas locaux/drafts, versions absentes et immuables, cycles, lot ordonné,
réponse altérée, recette privée, import refusé avant écriture et wrapper de lot.
Les GET de reconfirmation sont mockés, y compris 404, login, changement de SHA et
mutualisation de plusieurs notions sur la même URL ; aucun GET public exécuté.
