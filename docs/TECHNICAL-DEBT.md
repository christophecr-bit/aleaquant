# Dette technique et décisions — 30 septembre 2026

Ce fichier suit la dette **active**. Une tâche réalisée est retirée de la liste active
et reportée dans `CHANGELOG.md`. Toute modification de code doit mettre à jour les
deux documents pertinents avant le commit.

## Réalisé dans cette livraison

- La collecte planifiée enchaîne maintenant EuroMillions, Loto et Keno depuis
  `aleaquant-data`, puis les faits et, pour les deux premiers jeux, les profils et
  pages avec mini-histogrammes. Le SQLite commun est filtré par jeu ; les SHA des
  révisions sont vérifiés avant d'enregistrer l'avancement. Reprise après échec et
  second passage sans recalcul testés. Au 30/09, la base locale compte 1 985
  EuroMillions, 7 673 Loto et 19 465 Keno. La routine reste locale et ne publie rien.
- La régression des mini-histogrammes sur les pages de tirage est corrigée dans
  le générateur. Les 9 658 fiches EuroMillions/Loto ont été régénérées localement :
  toutes comportent les graphes des mesures scalaires pour lesquelles une loi est
  disponible (18 sur `LO-20260928`), chacun lié à la loi de son régime. Les queues
  non nulles conservent un pixel visible ; les signatures catégorielles restent
  textuelles. La légende distingue regroupement graphique et rareté de la
  classe exacte. Rien de cela n'a encore été déployé sur le Worker.
- Le gabarit de l'accueil éditorial est défini dans
  `docs/SITE-EDITORIAL-ARCHITECTURE.md` et illustré par la maquette locale : quatre
  rubriques avec cartes d'article, d'analyse, d'expérience, de référence ou de
  sujet à préparer. Les sujets non publiés sont signalés et sans lien.
- Covariance **théorique** des positions ordonnées k/N calculée en fractions exactes
  pour les régimes AleaQuant ; chaque cellule vérifiée sur de petits univers et la
  variance de l'étendue recoupée avec la loi exacte existante. Note de recherche
  dans `docs/research/covariance-positions-ordonnees.md`. Aucun indicateur public.
- Matrices **historiques exploratoires** estimées séparément sur sept groupes
  jeu/règle, avec effectifs, périodes et empreintes des révisions. Elles restent
  hors dictionnaire et hors site ; voir `docs/research/covariance-historique-par-jeu.md`.
- Les récits de tirage approuvés sont reliés aux pages par `research_pack.draw_id` :
  l'import vérifie l'identifiant et le SHA des faits, puis régénère uniquement la page
  concernée. L'article du 6 septembre 2011 (`EM-2011053`) est désormais présent sur
  sa page locale. Les autres pages gardent leurs faits sans récit tant que leur
  article n'a pas été approuvé.
- Pages Loto construites à partir des 7 673 fiches de faits ; URL par identifiant de
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
  **la qualification d'un audit** pour **chaque jeu et régime**. Une première
  estimation historique descriptive est disponible, sans test statistique.
  Leur covariance porte sur les **positions ordonnées d'un même tirage** ;
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
  Contrôler régulièrement la fraîcheur Keno : l'archive courante a été ajoutée
  au collecteur et la base atteint le 30/09/2026. Aucun article ni test d'audit
  calibré n'est encore réalisé.
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
- Qualifier les pages et profils Keno avant publication. Le pipeline local calcule
  les nouvelles fiches et a amorcé les 30 plus récentes ; le fonds historique
  complet n'est pas encore calculé dans `dist/data/facts`.
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
- Intégrer la maquette éditoriale au site après validation des quatre rubriques et
  des cartes de `docs/SITE-EDITORIAL-ARCHITECTURE.md`. Le fil des derniers tirages
  utilise encore un snapshot : le raccorder aux dernières révisions de chaque jeu.
  Générer les cartes depuis un manifeste de publications approuvées et de ressources
  curatées, sans exposer les brouillons. Tester de vrais textes sur mobile, puis
  choisir entre un portage Astro et une adaptation du site actuel. Le calendrier
  doit rester propre à chaque jeu ; le Journal est un fil transversal. Examiner
  Hostinger et Semnal comme références visuelles seulement.
- Publier la régénération des pages de tirage avec mini-histogrammes après revue
  des changements produits et contrôle du budget d'assets Wrangler. Le correctif
  fonctionne localement et passe les tests, mais le Worker sert encore l'ancienne
  version tant qu'un déploiement n'a pas été décidé.
- Construire l'Atlas de portefeuilles selon `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`.
  Le contrat est défini ; restent à faire : schéma de cohorte et niveaux de
  preuve, matrice de recherche Loto `(pool, taille de grille, budget, ordre de
  couverture, objectif)` incluant **pool 10 / 25 grilles**, solution et
  `RANDOM` au même budget, puis tailles 6 et 30 et autres cellules prioritaires.
  Conserver provenance, score et bornes de qualité ; ne parler d'optimum qu'avec
  preuve. Ajouter ensuite les cohortes EuroMillions/Keno pertinentes, la
  séparation index/fiches et les articles de fond. Garder Keno 10-numéros pour
  la première étape ; autres formats et régimes sont des cohortes distinctes.
  L'interface doit retrouver une solution précalculée ; si la cellule manque,
  signaler le calcul absent ou planifier une recherche hors ligne. Une commande
  légère peut seulement **mesurer** la géométrie de grilles apportées. Ne pas
  présenter les cinq démonstrations Loto comme une comparaison de performances,
  ni afficher rareté ou gain sans référence et évaluation adaptées.
- Étudier les garanties conditionnelles de roues `x if y of p` selon
  `docs/research/garanties-conditionnelles-portefeuilles.md` : vérificateur
  exhaustif indépendant du générateur, matrice des pires cas, contre-exemples,
  multiplicité garantie et comparaison `RANDOM` à budget égal. Le cas Loto
  pool 10 / 25 grilles doit séparer garantie sur les numéros principaux et
  rang qui dépend aussi du Chance ; EuroMillions et Keno exigent leurs propres
  barèmes/régimes. Ne pas qualifier un seuil de rang sans preuve complète.
- Étudier la réponse différée aux demandes d'optimisation absentes du catalogue :
  identifiant et statut persistants, déduplication des paramètres, quotas et
  exécution hors ligne reprenable sur la machine AleaQuant. Une notification
  courriel facultative attend un domaine et un service d'envoi configurés.
  Comparer ensuite sur de vrais lots coût et débit de ce moteur local avec
  Cloudflare Containers ; les Workers HTTP ne portent pas le calcul lourd.
  Détails et liens de prix datés dans `docs/ATLAS-GEOMETRIES-ARCHITECTURE.md`.
- Avant toute contribution sur une recherche personnalisée : mesurer temps
  machine et temps de revue sur plusieurs cellules, définir un périmètre et
  une durée de recherche bornés, dédupliquer les cellules déjà calculées et
  annoncer le montant avant accord du demandeur. Garder libre l'Atlas déjà
  publié ; ne vendre ni promesse d'optimum non prouvé ni perspective de gain.
  Aucun paiement n'est implémenté dans cette version.
- Vérifier le lien de déploiement GitHub–Cloudflare : le flux documenté actuellement
  reste `wrangler deploy` manuel, puis `git push`. Ne pas annoncer de CI non vérifiée.
- Surveiller la disponibilité des archives FDJ et renouveler les URL dans
  `../aleaquant-data/games/*.yaml` lorsqu'une période change. Les réponses de
  l'archive Keno peuvent brièvement diverger selon le cache : le 30/09, deux
  lectures successives ont donné le 29 puis le 30 comme dernier tirage ; les
  révisions déjà importées restent conservées.
- Surveiller le nombre d'assets Wrangler avant chaque extension du site. Si ce nombre
  approche 20 000 sur le plan gratuit, regrouper ou externaliser les données nécessaires
  aux pages avant d'ajouter de nouveaux fichiers.
