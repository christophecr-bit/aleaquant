# Dette technique et décisions — 30 septembre 2026

Ce fichier suit la dette **active**. Une tâche réalisée est retirée de la liste active
et reportée dans `CHANGELOG.md`. Toute modification de code doit mettre à jour les
deux documents pertinents avant le commit.

## Réalisé dans cette livraison

- Pages Loto construites à partir des 7 672 fiches de faits ; URL par identifiant de
  tirage pour préserver les séances multiples d'une même journée.
- Régimes Loto distingués : 6/49 avec complémentaire non cochée, puis 5/49 + Chance.
- Déploiement statique maintenu sous le plafond Worker par exclusion des JSON de faits
  intermédiaires avec `dist/.assetsignore`. Les faits restent dans Git. Le Worker a
  accepté 9 686 assets le 30/09/2026 ; deux pages Loto répondent en HTTP 200.
- Lois Keno exactes par récurrence pour 16 mesures sur 20, avec total de chaque loi
  vérifié contre C(n,k). Les mesures absentes sont déclarées dans `missing_fields`.

## Actif

- Vérifier les lois Keno 16/56 contre l'exhaustif HPC indépendant. Les tests sur
  petits domaines prouvent l'équivalence à l'énumération, mais pas ce contrôle HPC.
- Couvrir les quatre lois Keno encore absentes : `arithmetic_triples`,
  `longest_arithmetic_progression`, `clusteredness_close_pairs_5`, `sorted_gaps`.
  Ne pas afficher de badge de rareté pour un champ sans loi.
- Construire les faits Keno après validation des lois et qualifier les pages Keno.
  Le rendu à la demande et les groupes mensuels sont décrits dans `SCALING.md` ;
  mesurer un groupe Keno avant de supprimer les pages statiques existantes.
- Décider séparément la bascule EuroMillions vers le pilote générique ; l'équivalence
  de la composante principale ne valide pas les étoiles historiques.
- Automatiser le mode de composition éditoriale en batch, avec approbation humaine.
- Vérifier le lien de déploiement GitHub–Cloudflare : le flux documenté actuellement
  reste `wrangler deploy` manuel, puis `git push`. Ne pas annoncer de CI non vérifiée.
- Surveiller le nombre d'assets Wrangler avant chaque extension du site. Si ce nombre
  approche 20 000 sur le plan gratuit, regrouper ou externaliser les données nécessaires
  aux pages avant d'ajouter de nouveaux fichiers.
