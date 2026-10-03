# Déploiements AleaQuant

Décision actuelle (clarification du 03/10/2026) : **recette validée → production
directe**, sans staging distinct. Voir [la politique de livraison](CI-STAGING-PRODUCTION.md).
Les entrées ci-dessous conservent le contexte historique de chaque livraison.

## 3 octobre 2026 — recette protégée, séparée de la production

- Autorisation : préparer et héberger la version à valider, avec le parcours
  **recette → staging distinct → production** confirmé par Christophe.
- Worker `aleaquant-recette` : https://recette.aleaquant.org/ ; entrée maquette
  https://recette.aleaquant.org/maquette/. Access créé avant la route, politique
  existante réutilisée. Aucun nouvel accès accordé à un autre public.
- Configuration `wrangler.recette.jsonc` ; Wrangler **4.147.0**. Adresse
  workers.dev et previews désactivées. Snapshots locaux ignorés par Git.
- Premier lot `.recette/current` : version `cb3639cc-e73c-4b31-8692-dbc8f6c638ff`.
  Deuxième lot `.recette/lots/20261003-02` : **`0770c758-ea7c-4290-ae8e-264a086397a2`**,
  correction des liens de maquette pour rester sur l'origine recette.
- **10 029 assets** ; première livraison complète, puis 1 fichier modifié
  (`maquette/index.html`), 10 028 déjà présents. Les 20 033 entrées annoncées au
  scan Wrangler incluent les répertoires ; elles ne sont pas le compte d'assets.
- HEAD source `d737a646cf8bc78b2e3fff3a0c2d96b49cbfc1d3`, arbre dirty assumé :
  la recette copie le `dist/` local, pas un candidat de production validé.
  [Manifeste SHA](deployments/20261003-recette-assets.json).
- Empreinte publique finale :
  `5c02bcadb027ac4ce0871f47910746ab52a493555df99c7c5d768498d8403bd1`.
- Validation : 13 tests du préparateur + 1 test du budget, dry-run Wrangler,
  vérification SHA des 10 031 fichiers du snapshot (dont 2 fichiers de contrôle).
  Navigation authentifiée et fiches EM-26078, LO-20260928, KE-26365 contrôlées :
  respectivement 21, 18 et 18 histogrammes présents.
- Accès anonyme `/` et `/maquette/` : 302 vers Access ; workers.dev : 404.
  En-têtes noindex et CSP présents sur la maquette après connexion.
  [Résultats et limites détaillés](deployments/20261003-recette-verification.json).
- Production avant/après : version `0fca4e10-6695-4161-b51f-0bd7b7f6bbc1`
  inchangée, HTTP 200 et SHA identiques pour `/`, `/maquette/`, `/articles.json`.
- Aucun recalcul de faits, aucune génération ni approbation d'article, aucune
  modification du moteur HPC. Les modifications Git préexistantes sont conservées.
- Limites : le premier essai `wrangler dev --local` a atteint la limite de
  watchers et a été arrêté ; aucun service ajouté sur le Mac. Staging et CI
  restent à créer. Guide d'exploitation : [RECETTE.md](RECETTE.md).

## 2 octobre 2026 — publication après recalcul des trois jeux

- Autorisation humaine reçue après validation des recalculs.
- Worker `aleaquant`, https://aleaquant.org et adresse workers.dev.
- Version publiée : `054bb2da-c9d1-4788-9213-a3090e243637`.
- Version précédente (retour arrière) : `2a0f4c85-c06c-4b59-917e-e8f75da15e43`.
- Build versionné : `c1aa6639b` ; recalcul : `f0ba8fc18` ; Wrangler 4.147.0.
- 9 991 pages : 1 985 EuroMillions, 7 673 Loto, 333 Keno 16/56.
  Les faits Keno historiques restent locaux ; aucune page 20/70 ajoutée.
- Snapshot figé hors du dépôt ; manifeste SHA dans
  [20261002-facts-assets.json](deployments/20261002-facts-assets.json).
- Cloudflare : 1 fichier téléversé (`app.js`), 10 026 déjà présents. Le rendu
  des pages reconstruites était déjà présent ; aucune nouvelle analyse approuvée.
- Article EM-2011053 : texte, approbation et fiche source approuvée préservés ;
  sa nouvelle fiche demeure en attente de revalidation avant bascule.
- Tests après reconstruction : 129 tests web + 28 sous-tests réussis. Suite
  agents inchangée : 119 tests réussis lors de la validation du recalcul.
- Vérification distante : 16 réponses HTTP 200 identiques octet pour octet au
  snapshot (accueil, script, journal, index, trois jeux et article approuvé),
  sur les deux domaines ; quatre réponses 404 attendues pour les faits bruts
  et une ancienne page Keno. [Preuves](deployments/20261002-facts-verification.json).
- Le contrôle de pages local confirme histogrammes et sommes par dizaine.
  Les fichiers recalculés ne sont pas exposés directement comme assets JSON.


## 2 octobre 2026 — sous-totaux par dizaine

- Worker : `aleaquant` ; Worker URL et `aleaquant.org` déployés.
- Version : `2a0f4c85-c06c-4b59-917e-e8f75da15e43` (Wrangler 4.147.0).
- Assets : 10 000 fichiers envoyés, 27 déjà présents.
- Vérification : la fiche locale puis les deux URL distantes renvoient HTTP 200 ;
  `decade-sums-card` est présent sur la fiche EuroMillions du 29/09/2026.
- Les sources et le build restent à pousser vers GitHub depuis le Terminal du Mac.
  Aucune modification Git distante n'a été faite ici.

## 1er octobre 2026 — domaine aleaquant.org

Domaine actif chez Cloudflare, raccordé par Custom Domain au Worker `aleaquant`.
Site : https://aleaquant.org/ ; maquette : https://aleaquant.org/maquette/.
Aucun asset redéployé : version existante conservée. HTTPS vérifié (HTTP 200),
accueil, maquette et `/tirages/loto/LO-20260928/` identiques octet pour octet
à workers.dev. Route persistée dans `wrangler.jsonc`, workers.dev conservé.
Le terminal distant Cloudflare Access/Tunnel n’est pas encore configuré.


## 1er octobre 2026 — maquette distante et histogrammes

- Worker public : https://aleaquant.aleaquant.workers.dev
- Maquette : https://aleaquant.aleaquant.workers.dev/maquette/
- Version Cloudflare : `18285622-994a-42cc-9e0f-937b28c67f7a`.
- Commit des assets : `deedfc645c4e981d133d58690627053f1571ac42`.
- Wrangler : 4.145.0 ; 9 667 fichiers envoyés, 24 déjà présents, soit 9 691 assets.
- Déploiement depuis un export temporaire de `dist/` au commit indiqué,
  avec `wrangler deploy --assets <export>/dist`. Les modifications locales non
  commitées des lois et des articles ne sont pas incluses. `data/facts/**` reste
  exclu par `.assetsignore`.
- Accueil actuel conservé. Maquette publique sous `/maquette/`, avec avertissement
  de travail en cours, snapshot au 30/09/2026 et noindex. Source dans
  `prototypes/editorial-home/`, copie publiée dans `dist/maquette/`.

Vérification distante : accueil, maquette, illustration, index des jeux et trois
pages de tirage identiques octet pour octet à l'export Git. `LO-20260928` expose
18 graphes, `EM-26078` 21, `EM-2011053` 18. Les fiches sources renvoient 404.
Les quatre tests de pages Loto/EuroMillions passent avant déploiement.

## Incident de synchronisation Git — état historique

**Résolu pour le dépôt web le 2 octobre 2026** : push vers `origin/main` réussi
jusqu’au commit `7d8baab82`, incluant le build et le compte rendu de cette livraison.
Le constat ci-dessous décrit l’échec précédent ; le laboratoire reste un cas distinct.

Le push vers `origin/main` avait échoué : l'identifiant HTTPS du trousseau macOS
n'est pas accessible depuis cette session (`failed to get: -25320`). Les
commits sont locaux ; Cloudflare a bien reçu l'export décrit ci-dessus.
Depuis un Terminal du Mac disposant de l'accès GitHub :

```sh
git -C /Users/chris/aleaquant/aleaquant-web push origin main
```

Le laboratoire `/Users/chris/aleaquant/loto-keno-lab` n'a pas de remote configuré au
contrôle de cette livraison. Ses commits ne sont donc pas sauvegardés sur un
hébergeur Git. Aucun dépôt distant n'a été créé automatiquement.
