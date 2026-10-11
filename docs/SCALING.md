# Pages de tirage à la demande — décision de conception

Décision du 30/09/2026 : **ne pas ajouter une page HTML statique par tirage Keno**.
Conserver les pages EuroMillions et Loto déjà publiées pendant la transition.

## Pourquoi

- Le Worker actuellement publié contient environ 9 700 assets. Le plafond Workers Free est
  de 20 000 fichiers statiques par version.
- Les 19 465 tirages Keno créeraient au moins autant de pages nouvelles : avec les
  assets existants, le déploiement dépasserait 29 000 fichiers, avant même les futures
  fonctionnalités. Cette architecture est refusée par le budget Wrangler.
- Les 9 658 JSON de faits EuroMillions/Loto, environ 165 Mo sur disque, sont déjà
  exclus du déploiement et conservés dans Git. Cette optimisation ne suffit pas pour
  les pages Keno elles-mêmes.

## Exception de lancement — Keno actif 16/56

Le 02/10/2026, le générateur a été étendu pour produire localement les 333 fiches
du régime Keno actif 16/56, avec une URL stable par `draw_id`. Ce lot limité est une
exception de lancement : il ne crée aucune fiche HTML pour les 19 133 tirages de
l'ancien régime 20/70. Les JSON sources de faits restent exclus du déploiement via
`dist/.assetsignore` ; les fiches HTML portent le rendu nécessaire au lecteur.

Le contrôle local du budget compte environ 10 000 assets publiables, sous le plafond
de 20 000 du plan Workers Free. Cette vérification ne vaut pas déploiement. La voie
mensuelle à la demande décrite ci-dessous reste nécessaire pour rendre l'archive 20/70
consultable sans dépasser le budget.

## Direction retenue pour le pilote

1. Le dépôt `aleaquant-data` garde la source canonique des tirages, révisions et
   provenances. Le moteur produit des **faits publiables immuables** pour chaque
   `draw_id`, sous le régime historique exact, sans look-ahead.
2. Le build regroupe ces faits par **jeu + mois** dans des JSON versionnés, avec un
   manifeste `draw_id → groupe` par jeu (les identifiants EuroMillions ne contiennent
   pas tous la date complète). Un groupe mensuel est mis à jour quand un nouveau
   tirage arrive ; il représente un asset, et non une page par tirage. Mesurer sa
   taille et le temps de lecture sur Keno réel.
3. Une route Worker `/tirages/<jeu>/<draw_id>/` charge le groupe correspondant via
   `env.ASSETS.fetch()`, trouve l'identifiant exact et rend le HTML côté serveur.
   Le site garde des URL stables, du texte accessible et une page 404 pour un ID inconnu.
   Seules ces routes passent par le Worker ; CSS, images et pages éditoriales restent
   des assets statiques servis directement.
4. Le rendu partage un modèle de page multi-jeux : chaque métrique cite sa source,
   sa formule et son type de preuve. Une loi absente n'affiche pas de rareté. Les
   articles approuvés conservent leur empreinte et ne sont jamais régénérés en silence.
5. Un manifeste de build enregistre le nombre de tirages, les régimes, les empreintes
   des groupes et le nombre d'assets. Le déploiement échoue si les totaux ne concordent
   pas avec la base canonique ou si le budget d'assets est dépassé.

La liaison `ASSETS` et le routage sélectif `run_worker_first` sont prévus par
Cloudflare. Cette direction évite une nouvelle base en ligne pour le pilote. Si un
groupe mensuel se révèle trop gros ou si le rendu dépasse le budget CPU du plan,
évaluer D1 (requêtes indexées par `draw_id`) ou KV ; ne pas migrer sans mesure.

Un prototype **non publié** sous `prototypes/keno-on-demand/` a regroupé les 19 452
tirages bruts disponibles lors de sa mesure en 397 mois + un index. Le plus gros mois
fait 9 186 octets et le parse local médian environ 0,03 ms. Il rend déjà une URL
individuelle avec HTML initial, canonical et vrai 404. Depuis, la source compte 19 465
tirages et les faits sont calculés pour tous ; il faut regénérer les groupes avec les
faits, mesurer taille/latence, puis vérifier le rendu des deux régimes avant déploiement.

## SEO et qualité éditoriale

Chaque tirage garde une URL individuelle, mais la page doit renvoyer son titre,
ses faits et sa lecture propre directement dans le HTML (rendu côté serveur), avec
une URL canonique. Le sitemap n'inclut que les pages publiées et utiles. L'existence
d'une URL ou d'un gabarit répété ne garantit aucune indexation ; les analyses
massivement similaires et sans valeur ajoutée ne doivent pas être créées pour le SEO.

## Conditions avant migration

- Démontrer l'équivalence du HTML rendu pour plusieurs tirages EuroMillions et Loto,
  y compris les anciennes règles et les journées à deux tirages Loto.
- Tester un groupe Keno réel : taille (sous 25 Mo par asset), temps de lecture/parse,
  mémoire et réponse du
  Worker dans le plan réellement utilisé.
- Vérifier liens, sitemap, canonical, redirections éventuelles et cache HTTP.
- Faire un déploiement progressif, puis retirer les milliers de pages statiques
  seulement quand leurs URL dynamiques répondent à l'identique.
- Maintenir un mode local sans Cloudflare pour les tests et la revue éditoriale.

## Sources de contraintes

- [Limites Workers](https://developers.cloudflare.com/workers/platform/limits/)
- [Binding des assets et `run_worker_first`](https://developers.cloudflare.com/workers/static-assets/binding/)
- [Facturation du Worker pour les routes dynamiques](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/)
- [Principes Google pour JavaScript et le HTML initial](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Politique Google contre le contenu généré en masse sans valeur](https://developers.google.com/search/docs/essentials/spam-policies)
