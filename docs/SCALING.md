# Pages de tirage à la demande — décision de conception

Décision du 30/09/2026 : **ne pas ajouter une page HTML statique par tirage Keno**.
Conserver les pages EuroMillions et Loto déjà publiées pendant la transition.

## Pourquoi

- Le Worker actuellement publié contient 9 686 assets. Le plafond Workers Free est
  de 20 000 fichiers statiques par version.
- Les 19 452 tirages Keno créeraient au moins autant de pages nouvelles, avant même
  les fiches de faits et les futures fonctionnalités : cette architecture ne passe pas.
- Les 9 658 JSON de faits EuroMillions/Loto, environ 165 Mo sur disque, sont déjà
  exclus du déploiement et conservés dans Git. Cette optimisation ne suffit pas pour
  les pages Keno elles-mêmes.

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
