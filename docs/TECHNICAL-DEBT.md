# Dette technique et décisions — 30 septembre 2026

Ce fichier suit la dette **active**. Une tâche réalisée est retirée de la liste active
et reportée dans `CHANGELOG.md`. Toute modification de code doit mettre à jour les
deux documents pertinents avant le commit.

## Réalisé dans cette livraison

- Covariance **théorique** des positions ordonnées k/N calculée en fractions exactes
  pour les régimes AleaQuant ; chaque cellule vérifiée sur de petits univers et la
  variance de l'étendue recoupée avec la loi exacte existante. Note de recherche
  dans `docs/research/covariance-positions-ordonnees.md`. Aucun indicateur public.
- Les récits de tirage approuvés sont reliés aux pages par `research_pack.draw_id` :
  l'import vérifie l'identifiant et le SHA des faits, puis régénère uniquement la page
  concernée. L'article du 6 septembre 2011 (`EM-2011053`) est désormais présent sur
  sa page locale. Les autres pages gardent leurs faits sans récit tant que leur
  article n'a pas été approuvé.
- Pages Loto construites à partir des 7 672 fiches de faits ; URL par identifiant de
  tirage pour préserver les séances multiples d'une même journée.
- Régimes Loto distingués : 6/49 avec complémentaire non cochée, puis 5/49 + Chance.
- Déploiement statique maintenu sous le plafond Worker par exclusion des JSON de faits
  intermédiaires avec `dist/.assetsignore`. Les faits restent dans Git. Le Worker a
  accepté 9 686 assets le 30/09/2026 ; deux pages Loto répondent en HTTP 200.
- Lois Keno exactes par récurrence pour 17 mesures sur 20, avec total de chaque loi
  vérifié contre C(n,k). Les mesures absentes sont déclarées dans `missing_fields`.
- Prototype **local et optionnel** A/B/C pour EuroMillions/loto/keno : trois titres issus des
  faits, sélection humaine liée aux empreintes, essai direct avec angle et copie
  relue sous un nouveau SHA. Le batch qui constitue le fonds d'articles reste
  indépendant : aucun choix A/B/C, aucune passe de fluidité. EM-26078 conserve
  « Une grille qui traverse quatre dizaines » comme essai non publié.
- Paramètres du batch exposés en options facultatives (modèle, effort, fenêtre,
  empreinte de profil) ; profil Pydantic et parcours LangGraph court de
  validation/approbation dans `../aleaquant-editorial-agents`. Les défauts du
  batch web et les lots déjà lancés restent compatibles. Le manifeste des
  nouveaux lots conserve les SHA des faits et du prompt ; une collecte sur des
  faits modifiés est refusée.

## Actif

- Étudier Coronel-Brizio et al., « Statistical auditing and randomness test of lotto
  k/N-type games » (2008, https://arxiv.org/abs/0806.4595), comme piste d'audit
  AleaQuant et d'article de fond. La partie théorique et son lien avec `span` sont
  vérifiés dans `docs/research/covariance-positions-ordonnees.md` ; restent
  **l'estimation historique et la qualification d'un audit** pour **chaque jeu et
  régime**. Leur covariance porte sur les **positions ordonnées d'un même tirage** ;
  elle n'est pas une autocovariance entre tirages. Comparer prudemment la matrice
  théorique aux estimations historiques par période homogène (taille,
  changement de règle, données manquantes, multiplicité des tests, Monte-Carlo).
  Étudier les dépendances restantes avec les autres métriques de géométrie,
  en évitant de compter des grandeurs dépendantes comme preuves indépendantes.
  Tester séparément une éventuelle autocovariance à décalage temporel si l'on veut
  auditer l'indépendance entre tirages. Décider ensuite si un indicateur agrégé
  d'audit mérite le dictionnaire ; ne pas ajouter une « rareté de covariance » à
  chaque tirage. Préparer un article sur covariance, étendue et contrôle du hasard,
  sans interprétation prédictive. Proposition de registre à qualifier :
  `theory.main.order_position_covariance@v1` pour la matrice attendue sous le
  modèle k/N ; `history.main.order_position_covariance@v1` pour la matrice
  estimée sur les tirages comparables. Libellé court commun : « Covariance des
  positions ». Libellé long historique : « Matrice de covariance entre les
  numéros classés par ordre croissant, estimée sur l'historique comparable ».
  L'entrée historique devra porter jeu, régime, période, effectif, méthode
  d'estimation et référence de la matrice théorique ; ce n'est pas un fait de
  tirage individuel. Préfixer les clés publiées par jeu, par exemple
  `euromillions.history.main.order_position_covariance@v1`, et conserver
  `rule_id` ou `k/N` dans chaque résultat ; Loto et Keno ont plusieurs régimes.
  Ne pas mêler étoiles EuroMillions ou Chance Loto aux numéros principaux.
  Aucun calcul historique ni article n'est encore réalisé.
- Produire puis relire les articles manquants, par lots quotidiens, pour arriver à
  un récit approuvé par tirage. Aujourd'hui l'association est possible mais le fonds
  d'articles est incomplet ; ne jamais afficher un brouillon comme article.
  Étendre la route d'article aux pages Keno lorsque leur rendu sera qualifié.
- Construire un histogramme HPC indépendant des lois de forme 16/56 si une
  qualification supplémentaire est requise : les artefacts HPC actuels évaluent
  des portefeuilles et ne fournissent pas ces distributions. Les récurrences ont
  été confrontées aux petits univers exhaustifs ; la nouvelle loi des paires
  proches passe aussi un contrôle indépendant du premier moment.
- Couvrir les trois lois Keno encore absentes : `arithmetic_triples`,
  `longest_arithmetic_progression`, `sorted_gaps`.
  Ne pas afficher de badge de rareté pour un champ sans loi.
- Construire les faits Keno après validation des lois et qualifier les pages Keno.
  Le rendu à la demande et les groupes mensuels sont décrits dans `SCALING.md` ;
  mesurer un groupe Keno avant de supprimer les pages statiques existantes.
  Un prototype brut a regroupé 19 452 tirages en 397 mois ; il faut maintenant
  intégrer les faits précalculés et mesurer de nouveau taille et temps de rendu.
- Décider séparément la bascule EuroMillions vers le pilote générique ; l'équivalence
  de la composante principale ne valide pas les étoiles historiques.
- Continuer à régler le batch de composition pour constituer la base d'articles.
  Mesurer qualité, gardes, coût et rendement sur un lot avant import ; conserver
  l'approbation humaine avant toute publication. Ne pas y intégrer les règles du
  futur comité LangGraph par défaut.
- Qualifier le parcours court sur un vrai lot collecté : vérifier la liaison
  manifeste → brouillon → faits → décision humaine, puis l'import manuel au site.
  Il contrôle les empreintes et les gardes déclarés, mais ne recalcule pas les
  lois ; prévoir une voie explicite pour reprendre un refus avec nouvelle version.
  Étendre ensuite le profil aux tirages Loto/Keno et à leurs régimes.
- Transférer l'expérience A/B/C et la relecture de fluidité au dépôt canonique
  `../aleaquant-editorial-agents` seulement après évaluation sur un lot varié :
  comparer les titres à l'aveugle, mesurer diversité des angles, rejets des gardes,
  qualité du corps, coût et temps. Comparer d'abord `gpt-5.4-mini` en effort `low`
  et un effort supérieur pris en charge, puis seulement si nécessaire un modèle plus
  fort. Le test réel EM-26078 a choisi un angle géométrique juste mais le premier corps
  gardait des répétitions ; la passe de fluidité les réduit modestement, sans rendre
  le texte publiable sans relecture. Généraliser le choix d'angle aux autres jeux
  seulement après cette évaluation, et prévoir des métadonnées de jeu/date séparées
  du titre sur les cartes de journal.
- Repenser l'éditorial de la page d'accueil : clarifier la promesse pour un nouveau
  lecteur, découper les longs textes en sous-parties, hiérarchiser les outils et
  choisir quelques blocs visuels/interactifs sobres. L'accueil mélange aujourd'hui
  introduction, mini-expérience, explorateur EuroMillions, Atlas, dictionnaire,
  journal et méthode; décider ce qui doit rester sur l'accueil et ce qui doit vivre
  sur une page dédiée, notamment le calendrier propre à chaque jeu. Prototyper une
  structure avant de retoucher les styles ou d'ajouter des animations. Une première
  maquette HTML autonome existe dans `prototypes/editorial-home/index.html` : cadre
  général, mini-expérience et rubriques actuelles sous forme de cartes, hiérarchie
  asymétrique, illustration abstraite et fil éditorial des derniers tirages avec des
  commentaires descriptifs plus fluides. Elle reste une piste non publiée et le fil
  utilise un snapshot local : il faut le relier aux données actualisées de chaque jeu.
  La tester avec de vrais textes et sur mobile, puis décider si elle doit être portée
  dans un prototype Astro ou adaptée directement au site actuel. Examiner Hostinger
  et Semnal comme références visuelles seulement; garder le code final transférable
  dans le dépôt actuel.
- Remettre l'Atlas dans la feuille de route produit : définir une première version de
  portefeuilles, ses familles et leurs limites, puis écrire des articles de fond AleaQuant
  qui introduisent la géométrie des grilles avant de présenter les outils. Les articles
  doivent expliquer couverture, recouvrement et dispersion sans promesse de gain ni
  confusion entre organisation d'un portefeuille et probabilité du tirage.
- Vérifier le lien de déploiement GitHub–Cloudflare : le flux documenté actuellement
  reste `wrangler deploy` manuel, puis `git push`. Ne pas annoncer de CI non vérifiée.
- Surveiller le nombre d'assets Wrangler avant chaque extension du site. Si ce nombre
  approche 20 000 sur le plan gratuit, regrouper ou externaliser les données nécessaires
  aux pages avant d'ajouter de nouveaux fichiers.
