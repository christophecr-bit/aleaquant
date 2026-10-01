# Déploiements AleaQuant

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

## Synchronisation Git à terminer

Le push vers `origin/main` a échoué : l'identifiant HTTPS du trousseau macOS
n'est pas accessible depuis cette session (`failed to get: -25320`). Les
commits sont locaux ; Cloudflare a bien reçu l'export décrit ci-dessus.
Depuis un Terminal du Mac disposant de l'accès GitHub :

```sh
git -C /Users/chris/aleaquant-web push origin main
```

Le laboratoire `/Users/chris/loto-keno-lab` n'a pas de remote configuré au
contrôle de cette livraison. Ses commits ne sont donc pas sauvegardés sur un
hébergeur Git. Aucun dépôt distant n'a été créé automatiquement.
