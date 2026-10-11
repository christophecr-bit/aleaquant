# Première v0 — préparation et validation manuelles

Version : 1.2 · 11 octobre 2026 · État : accueil proposé, lancement non autorisé

Chris choisit une première livraison manuelle avec Codex. La structure retenue
est un accueil court : derniers tirages, un article à la une et quatre portes
vers Comprendre, Atlas, Recherche et Méthode. Le rappel du 11 octobre rétablit
explicitement les publications scientifiques décryptées et reliées à AleaQuant,
en complément de la méthode propre au projet. Cette décision ne valide pas encore les textes
ni un déploiement. Le flux reste recette protégée → lot validé → production,
sans attendre une CI ou un troisième environnement.

## Ce qui est vérifié au 10 octobre

| Élément | État observé |
|---|---|
| Production `aleaquant.org` | Accueil HTTP 200, différent du travail local ; manifeste EuroMillions au 29 septembre, EM-26078, 1 985 tirages. |
| Données locales | EuroMillions au 9 octobre, EM-26081, 1 988 tirages ; les derniers résultats Loto et Keno disponibles ont leurs fiches. |
| Article intégré | Un seul : `tirage-EM-2011053`, titre « EuroMillions — tirage du 6 septembre 2011 », approuvé le 30 septembre par Christophe. Journal public identique au JSON local lors de l'audit. |
| Accueil et maquette existants | Ancien accueil long ; maquette `/maquette/` conservant des résultats de septembre et des sujets non publiés. Ils ne constituent pas la nouvelle v0 validée. |
| Nouveau glossaire et Atlas | Locaux ; `/comprendre/glossaire/` et `/portefeuilles/` répondent HTTP 404 en production lors de l'audit. |
| Recette distante | Répond par redirection vers Access ; contenu authentifié non revérifié dans cet audit. |
| Contrôle documentaire | Bloqué : 46 notions de l'Atlas sans preuve publique ; article historique non inventorié au SHA exact. |
| Taille du lot local | 10 060 assets lors de l'audit, sous la borne configurée de 20 000. |

Preuve datée et empreintes :
[relevé de l'audit](</Users/chris/Documents/Codex/2026-10-09/peu/work/v0-release-audit-2026-10-10.json>).
Les constats HTTP sont une observation à cette date, pas une garantie de fraîcheur
future. Aucun accès authentifié recette, recalcul scientifique ou déploiement
n'a été réalisé pour cet audit.

## Contenu à relire par référence

L'aperçu et son manifeste sont dans `prototypes/v0-homepage-review/`. Le manifeste
est en attente de revue humaine. Les liens de consultation visent l'aperçu local
existant, pas une promesse de disponibilité publique.

Consultation de cette proposition : <http://127.0.0.1:4192/>. Pour relancer
l'aperçu depuis le dépôt, dans un terminal dédié :

```sh
python3 -m http.server 4192 --bind 127.0.0.1 --directory prototypes/v0-homepage-review
```

Les destinations existantes utilisent le serveur local du site sur le port 4178.
Si celui-ci est arrêté, le relancer dans un second terminal depuis le dépôt :

```sh
python3 -m http.server 4178 --bind 127.0.0.1 --directory dist
```

Revue visuelle réelle effectuée sur ordinateur et mobile, y compris une largeur
de 320 pixels sans débordement horizontal. Les sept références, les empreintes
du manifeste et des sources et la seule insertion d'ID dans la page de l'article
ont été contrôlées. [Preuves de revue](</Users/chris/Documents/Codex/2026-10-09/peu/work/v0-homepage-qa-2026-10-10.json>).
Ces contrôles ne constituent pas une validation des textes par Chris.

La révision v0.2 ajoute une introduction locale de Recherche & méthode dans
`recherche-et-methode.html`. Les références RESEARCH-INTRO, RESEARCH-PUBLICATIONS
et RESEARCH-METHOD permettent d'en demander une retouche. Aucun article scientifique
externe n'est présenté comme déjà publié. L'aperçu v0.1 est conservé, avec empreintes
vérifiées ; son emplacement figure dans `review-manifest.json`.

| Référence | Contenu de la proposition | Destination ou objet |
|---|---|---|
| HOME-HERO | « Le hasard a des structures. Explorons-les. » et promesse courte actuelle. | Introduction de l'accueil. |
| HOME-DRAWS | Derniers résultats locaux EuroMillions, Loto et Keno, sans article fictif. | Fiches de tirages réelles, résultats tirés des JSON locaux. |
| HOME-FEATURED | « EuroMillions — tirage du 6 septembre 2011 », annoncé comme historique. | Article `tirage-EM-2011053`, version humaine existante. |
| HOME-COMPRENDRE | Porte vers les définitions accessibles. | Glossaire local, à publier avant les pages dépendantes. |
| HOME-ATLAS | Porte vers les études et portefeuilles. | Catalogue local `/portefeuilles/`, encore bloqué pour publication. |
| HOME-RESEARCH | Publications scientifiques expliquées et reliées à AleaQuant. | Introduction locale `recherche.html`, articles en préparation. |
| HOME-METHODE | Construction et évaluation des portefeuilles. | Pipeline existant sur le port 4178, `/portefeuilles/`. |
| HOME-FOOTER | Rappel bref et navigation utile. | Limites et liens vérifiés. |

Une demande « modifier HOME-HERO » vise le bloc d'accueil. Une demande
« modifier l'article tirage-EM-2011053 » vise le texte de l'article, indépendamment
de son emplacement. Un nouveau titre ne crée pas un nouvel ID.

SHA approuvé de l'article historique :
`ea1f2ae0c05538cc7e257b981b6a6e6b4d316079ec43c65a9f1df6222af8fa4e`.
La présentation locale ajoute sa référence, sans toucher au brouillon, aux faits
ou à cette décision. Une retouche de texte produira une version et un SHA à
relire ; la conservation durable des éditions est suivie dans TD-EDIT-002.

## Ce qui reste avant de publier

1. Faire valider les textes et la sélection de l'accueil. Reprendre les blocs
   demandés, versionner le manifeste et conserver la révision effectivement relue.
2. Préparer les destinations définitives. Le nouvel accueil ne peut remplacer
   l'ancien en conservant des liens vers des ancres qui disparaîtraient ; préserver
   l'expérience, la méthode et la navigation des fiches dans des routes réelles.
3. Inventorier les notions de tous les contenus retenus, y compris l'article
   historique. Résoudre l'amorçage documentaire en préservant le site public :
   un upload du glossaire seul retirerait les autres assets du Worker. Ne pas
   supprimer les dépendances ou le contrôle pour forcer le lancement.
4. Préparer puis contrôler un lot complet figé : contenu approuvé, identités,
   références, mobile, navigation, fraîcheur annoncée, données et empreintes.
   Faire relire ce lot en recette, puis recueillir « bon pour production » sur
   sa version exacte. Une validation de l'accueil seule ne valide pas le lot.
5. Publier les prérequis dans l'ordre qualifié, enregistrer leurs réponses publiques,
   puis livrer les contenus dépendants quand la garde passe. Vérifier la production
   et consigner version Worker, empreintes, validation et sauvegarde Git.

Le point 3 est un blocage actuel, pas une action déjà qualifiée. Les commandes
de rapport restent sans déploiement :

```sh
python3 scripts/check_content_dependencies.py
python3 scripts/deploy_site.py
```

L'absence de CI, la console d'exploitation, les profils d'agents PB-017 et la
vitrine texturée avec explorateur PB-018 peuvent suivre la v0. Ces fonctionnalités
ne deviennent pas des promesses de l'accueil avant leur livraison.

Registres : OPS-008 (lancement), OPS-009 (corrections), TD-DOC-001 (prérequis),
TD-EDIT-002 (éditions), PB-001 (accueil) et PB-003 (articles).

Historique : v1.1 (11 octobre) précise Recherche & méthode et la révision d'aperçu
v0.2 ; v1.0 (10 octobre) prépare la première revue manuelle.

Révision v1.2 / aperçu v0.3 (11 octobre) : Recherche et Méthode séparées à la
demande de Chris. HOME-RESEARCH ajouté ; HOME-METHODE conservé. Introduction
Recherche : RESEARCH-INTRO et RESEARCH-PUBLICATIONS ; RESEARCH-METHOD retiré
de cette rubrique. La révision v0.2 est conservée dans le dossier de travail.
