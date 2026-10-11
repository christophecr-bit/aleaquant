# Prototype Keno : 1 fichier par jeu et mois, page à la demande

Ce dossier n'appartient pas au site publié. Les données sont extraites en lecture seule de
`aleaquant-data/data/aleaquant.sqlite3` (dernière révision de chaque tirage Keno).
Par défaut, le dépôt de données est attendu comme frère de `aleaquant-web` ; définir
`ALEAQUANT_DATA_DB` pour utiliser un autre chemin. `python3 build_shards.py`
reconstruit les 397 fichiers mensuels et `index.json` sous `assets/` (ignoré par Git).
`node check.mjs` contrôle les données et les réponses HTML sans réseau ni déploiement.

## Mesures locales (30 septembre 2026)

- 19 452 tirages, du 16 septembre 1993 au 17 septembre 2026, soit 397 mois.
- 398 assets au total : 397 mois et 1 index. Les assets publics actuels du site sont
  environ 9 690 ; l'ajout porterait le nombre à environ 10 088, sous le plafond de
  20 000 sur Workers Free. Ce compte doit être refait avant intégration.
- Tous les fichiers mensuels totalisent 2 870 637 octets bruts et 568 853 octets
  compressés gzip. Mois médian : 8 862 octets bruts, environ 1 707 octets gzip ;
  plus gros mois : 9 186 octets bruts, 1 779 octets gzip.
- L'index identifiant → mois fait 467 130 octets bruts, 40 600 octets gzip.
- Sur Node 25 local, 5 000 lectures JSON du mois médian : environ 0,031 ms par lecture.
  Plus gros mois : environ 0,027 ms. L'index : environ 2,82 ms par lecture, sur
  1 000 répétitions. Ce sont des temps de parse, sans réseau ni latence Worker.

## Route et cache

L'URL publique prévue est `/tirages/keno/<draw_id>/` : par exemple
`/tirages/keno/KE-26350/`. La date n'est pas une clé unique avant novembre 2025,
quand il existait deux tirages quotidiens. L'index donne le mois pour un identifiant,
puis le Worker lit uniquement le fichier de ce mois et produit le HTML côté serveur.
Un identifiant absent rend un vrai HTTP 404 avec `noindex`. Une erreur de lecture de
shard rend 503, pour éviter de signaler à tort une disparition du tirage.

Le Worker garde l'index en mémoire pendant la vie de son isolate. La page annonce
`max-age=300, s-maxage=3600` ; le cache effectif en production doit être mesuré et
contrôlé avec une correction de tirage. Les données mensuelles peuvent être mises en
cache indépendamment, à condition d'invalider lors d'une nouvelle révision.

## Intégration envisagée

Copier les shards dans `dist/keno/`, placer le Worker dans le dépôt, puis ajouter
`main`, `assets.binding: "ASSETS"` et
`assets.run_worker_first: ["/tirages/keno/*"]` à la configuration Wrangler.
La syntaxe de `run_worker_first` et du binding est celle de la documentation
Cloudflare : https://developers.cloudflare.com/workers/static-assets/binding/ .
Le Worker doit laisser les autres routes statiques au service d'assets.

Le rendu actuel expose seulement les boules, la date, la séance et la formule réelle
(20/70 historique ou 16/56 actuel). Il contient un titre, une description, une URL
canonique et des données structurées dans le HTML initial, lisibles sans JavaScript.
Avant publication, il faut intégrer les faits calculés par le moteur générique,
adapter la présentation au site, ajouter une page d'index Keno et les URL au sitemap.
Ces faits doivent être préparés à la construction et regroupés par mois ; le Worker
ne doit pas recalculer l'historique à chaque requête. Mesurer alors la taille des
shards enrichis et vérifier le budget. Les données brutes seules ne constituent pas
une fiche d'analyse Keno publiable.

## Contrôles exécutés

`check.mjs` vérifie l'unicité et la correspondance des 19 452 identifiants,
la formule et le nombre de boules, la présence de dates avec deux tirages,
la génération HTML du premier et du dernier tirage, l'URL canonique, JSON-LD,
la réponse 404 et la requête HEAD. Le prototype ne modifie ni `dist`, ni le code
de génération de pages, ni la configuration de déploiement du site.
