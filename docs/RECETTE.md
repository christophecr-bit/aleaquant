# Recette AleaQuant

**Auteur :** AleaQuant · **Date :** 2026-10-03 · **Version :** 1.2.
**Historique :** 1.0 recette isolée ; 1.1 liens internes ; 1.2 recette validée → production directe.

La recette héberge un lot figé à valider sur `recette.aleaquant.org`, avec le
Worker séparé `aleaquant-recette`. **Une fois validé pour publication, le lot passe
directement en production sur `aleaquant.org`.** La recette remplit le rôle de
staging ; aucun environnement supplémentaire n'est prévu. La livraison est encore
manuelle, la CI reste à réaliser. `private.aleaquant.org` reste le tunnel vers le Mac.

## État vérifié le 3 octobre 2026

- Site : https://recette.aleaquant.org/ ; **maquette : https://recette.aleaquant.org/maquette/**.
- Access activé avec la politique d'identités existante ; sans session, HTTP 302
  vers la connexion Access. `workers.dev` désactivé (HTTP 404).
- Version Worker : `0770c758-ea7c-4290-ae8e-264a086397a2`.
- Lot déployé : `.recette/lots/20261003-02/dist`, **10 029 assets**. Manifeste
  versionné dans [deployments/20261003-recette-assets.json](deployments/20261003-recette-assets.json).
- Maquette et navigation authentifiées contrôlées ; histogrammes présents sur
  les fiches témoins EuroMillions (21), Loto (18) et Keno (18).
- En-têtes noindex et CSP contrôlés sur Cloudflare. Production inchangée.
- 13 tests du préparateur et 1 test du budget d'assets réussis.

La configuration garde `.recette/current/dist` comme destination par défaut du
premier lot. **Pour redéployer le lot ci-dessus, conserver son `--assets` explicite** :

```sh
npx --no-install wrangler --config wrangler.recette.jsonc deploy --assets .recette/lots/20261003-02/dist
```

Ce lot vient d'un arbre de travail contenant des changements préexistants non
committés, tracés par leurs empreintes. Il est destiné à la validation, sans
promotion automatique. La maquette garde ses données de démonstration datées ;
son fil des derniers tirages n'est pas encore alimenté dynamiquement.

## Protection et isolation

Créer et vérifier l'application Cloudflare Access pour `recette.aleaquant.org`
avant de publier sa route. Une politique doit limiter les connexions aux
identités autorisées. La configuration recette désactive `workers.dev` et les
URL d'aperçu, afin d'éviter une deuxième entrée publique.

`wrangler.recette.jsonc` est indépendant de `wrangler.jsonc` : le Worker et le
domaine de production ne sont pas modifiés. Le snapshot ajoute seulement dans
sa copie `X-Robots-Tag: noindex, nofollow, noarchive` et un `robots.txt` avec
`Disallow: /`. Ces règles de référencement complètent Access; elles ne sont pas
une authentification. Les en-têtes CSP et de sécurité existants sont conservés.

Dans les copies HTML, les `href` des balises `<a>` pointant exactement vers
`aleaquant.org` ou `aleaquant.aleaquant.workers.dev` deviennent des URL relatives
à l'origine : la navigation reste sur la recette, avec chemin, requête et fragment
conservés. Les liens externes, canonical, scripts, textes et faits restent intacts.
Le manifeste nomme ces adaptations dans `overlays`; `dist/` n'est pas modifié.

## Préparer et vérifier le lot

Depuis la racine du dépôt, avec Python 3 et Wrangler **4.147.0** déjà installé :

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_prepare_recette.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_asset_budget.py
python3 tools/prepare_recette.py
npx --no-install wrangler --config wrangler.recette.jsonc deploy --dry-run
```

La préparation copie le `dist/` local dans `.recette/current/dist` sans build,
sans rafraîchissement des tirages et sans déploiement. `data/facts/**` est exclu.
Toute nouvelle règle `.assetsignore` non prise en charge provoque un refus
explicite. Un dépassement de 20 000 assets, un lien symbolique ou une modification
des sources ou de l'état Git détectée pendant la copie provoque aussi un refus.

Le manifeste `.recette/current/manifest.json` reste **hors des assets** : il
enregistre HEAD Git, l'état dirty explicite, les chemins, tailles, SHA-256 des
sources et des copies, ainsi que l'empreinte globale du contenu public. HEAD est
un repère de provenance; les fichiers locaux modifiés ne sont pas attribués à
un commit propre. Relire ce manifeste et le lot avant toute publication.

Une destination existante est refusée pour préserver le lot déjà validé.
Pour une nouvelle recette, préparer un nouveau dossier, puis passer les mêmes
assets explicitement à Wrangler :

```sh
python3 tools/prepare_recette.py --output .recette/lots/lot-002
npx --no-install wrangler --config wrangler.recette.jsonc deploy --dry-run --assets .recette/lots/lot-002/dist
```

Les snapshots sont ignorés via `.recette/.gitignore`. Un dry-run prépare la
commande sans publier; il ne prouve pas que Cloudflare Access est actif.

## Publication et recette humaine

Une fois Access vérifié et le lot choisi approuvé pour son exposition en recette :

```sh
npx --no-install wrangler --config wrangler.recette.jsonc deploy
```

Pour un autre lot, conserver `--assets .recette/lots/lot-002/dist` sur cette
commande. La configuration doit toujours être précisée pour cibler le Worker
recette. Cette commande publie uniquement en recette.

Vérifier l'accès sans session (authentification Access exigée), puis avec
l'identité autorisée : accueil `/`, entrée éditoriale `/maquette/`, `/tirages/`,
les trois jeux, une fiche de chaque jeu, les scripts et histogrammes. Vérifier
les en-têtes noindex et la réponse 404 de `/data/facts/EM-26078.json`.
`articles.json` appartient au lot public : contrôler ses statuts et son contenu
avant publication, même si seules les pages d'articles approuvés sont rendues.

Consigner l'identifiant de version Worker, l'empreinte du manifeste, la date et
les vérifications dans le journal de livraison. Toute nouvelle préparation
produit un lot à valider de nouveau. La validation « bon pour production »
autorise la livraison directe de ce lot en production : mêmes contenus approuvés,
avec les adaptations d'environnement documentées (notamment retrait des règles
noindex/robots propres à la recette). Aucune régénération du contenu à cette étape.
Cette clarification du processus ne vaut pas validation du lot actuellement en recette.
