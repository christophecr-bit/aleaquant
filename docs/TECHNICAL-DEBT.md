# Dette technique active — 2 octobre 2026

Auteur : AleaQuant · v2.3

Ce registre ne contient que des composants d'ingénierie, des validations techniques
et des tâches d'exploitation encore nécessaires. Les fonctions attendues sont dans
[`ROADMAP.md`](ROADMAP.md) ; les choix de structure sont dans les documents
`*-ARCHITECTURE.md` ; les expériences et articles sont au comité éditorial. Une
entrée terminée quitte cette liste et rejoint `CHANGELOG.md`.

## Site et publication

- [ ] **Publier les notes de version du modèle** : générer depuis le registre
  versionné de `aleaquant-data/docs/MODEL-CHANGELOG.md` une page indexée et un
  résumé de dernière version ; conserver liens vers preuves, commits et portée
  des recalculs. Toute note publique demande une revue humaine.
- [ ] **Publier l'alignement des histogrammes** : les pages locales ont été
  régénérées avec une barre par classe, comme l'accueil. Déployer puis vérifier une
  page Loto et une page EuroMillions ; aucun calcul de loi ne doit changer.
- [ ] **Relier la console éditoriale au site** : après approbation du SHA exact,
  enregistrer la rubrique choisie dans le manifeste de publications, produire une
  prévisualisation, puis importer le contenu dans le générateur du site. Tester les
  quatre rubriques, le Journal transversal, une correction versionnée et le refus
  d'une publication sans approbation. La fonction produit est décrite dans
  [`ROADMAP.md`](ROADMAP.md) ; la console et le graphe sont dans le dépôt
  [`aleaquant-editorial-agents`](../../aleaquant-editorial-agents/docs/roadmap-editorial-agentique.md).
- [ ] **Raccorder la maquette éditoriale aux contenus réels** : générer les cartes
  depuis le manifeste approuvé et les dernières révisions par jeu, retirer le
  snapshot des derniers tirages, empêcher l'exposition des brouillons et valider
  les vues mobile/desktop. Appliquer le gabarit décidé dans
  [`SITE-EDITORIAL-ARCHITECTURE.md`](SITE-EDITORIAL-ARCHITECTURE.md).
- [ ] **Terminer la publication Keno** : publier et vérifier les 333 fiches locales du
  régime actif 16/56 ; servir ensuite les 19 133 anciens tirages 20/70 avec un index
  compact et une résolution d'URL à la demande, sans fabriquer des milliers de pages
  statiques. Vérifier accès direct, séparation des régimes, faits, SEO, latence et
  budget d'assets. Référence : [`SCALING.md`](SCALING.md).
- [ ] **Construire les briques de l'archive tabulaire** : index par `draw_id` et
  régime, requête/pagination côté serveur, sérialiseur CSV/JSON versionné avec
  dictionnaire et provenance, tests de complétude SHA et mesure du budget d'assets.
  La fonction destinée aux utilisateurs est dans [`ROADMAP.md`](ROADMAP.md).

## Calculs et données

- [ ] **Qualifier et clôturer la convergence du générateur de facts** : la voie
  normale de `tools/refresh_draws.py` appelle maintenant `engine/facts_generic.py`
  pour EuroMillions, Loto et Keno ; `engine/build_data.py` conserve le constructeur
  historique EuroMillions derrière `--legacy-facts` comme rollback/oracle. La sortie
  complète des 1 985 snapshots EuroMillions est paritaire, hors nouveau
  `F.main.decade_sums`, et les tests ciblés passent. Restent à faire : qualification
  stricte des configurations YAML, exécution réelle de rafraîchissement en local,
  vérification d'un échantillon de sorties et observation avant de retirer le chemin
  historique. Ne pas recalculer/écraser les facts existants à SHA source inchangé ;
  ne retirer `--legacy-facts` qu'après validation d'exploitation. L'extraction du
  moteur dans `aleaquant-data` est différée, ce n'est pas une dette de la bascule
  actuelle. Contrat et état : [`ARCHITECTURE.md`](../../aleaquant-architecture/ARCHITECTURE.md#51-décision--un-moteur-de-tirage-configuré-par-jeu).
- [ ] **Compléter ou qualifier les lois historiques Keno 20/70** pour
  `arithmetic_triples`, `longest_arithmetic_progression` et `sorted_gaps`. Garder
  ces champs explicitement absents tant qu'ils ne sont pas qualifiés ; ne pas
  afficher de classe de rareté sans loi.
- [ ] **Comparer indépendamment les histogrammes Metal sur tout C(56,16)**.
  Les vérifications CPU par fenêtres et les preuves de masse/continuité sont
  acquises ; consigner méthode, empreintes, sommes de contrôle et écarts éventuels.
- [ ] **Automatiser la vérification de fraîcheur des sources** : détecter les
  divergences temporaires de l'archive FDJ, journaliser la révision retenue et
  alerter sans écraser les révisions déjà importées. Configuration des jeux dans
  `../../aleaquant-data/games/*.yaml`.

## Livraison et exploitation

- [ ] **Rendre le déploiement reproductible** : vérifier le lien GitHub–Cloudflare,
  créer les environnements recette/production prévus dans
  [`CI-STAGING-PRODUCTION.md`](CI-STAGING-PRODUCTION.md), séparer les secrets et
  exécuter les contrôles/tests avant déploiement. Le flux actuellement vérifié
  reste manuel (`wrangler deploy`, puis `git push`).
- [ ] **Rétablir une sauvegarde Git distante vérifiable** : résoudre l'accès HTTPS
  au trousseau macOS et pousser les commits locaux ; ne pas considérer un
  déploiement Worker comme une sauvegarde du dépôt. État et procédure dans
  [`DEPLOYMENTS.md`](DEPLOYMENTS.md).
- [ ] **Contrôler automatiquement le budget Wrangler** : compter les assets du
  build et échouer avant déploiement si la limite configurée approche ; documenter
  les exclusions et les fichiers servis à la demande.
- [ ] **Finaliser les URL du domaine propre** : canonicals, sitemap/RSS et
  redirections `workers.dev`/`www` cohérents avec `aleaquant.org`.
- [ ] **Vérifier l'accès SSH distant via Access/Tunnel** séparément du site public,
  puis documenter le démarrage, la reprise après veille et la disponibilité après
  redémarrage du Mac.

## Hors de ce registre

- Fonctions et priorités utilisateur : [`ROADMAP.md`](ROADMAP.md).
- Structure du site et du catalogue de contenus :
  [`SITE-EDITORIAL-ARCHITECTURE.md`](SITE-EDITORIAL-ARCHITECTURE.md).
- Atlas, cohortes et garanties conditionnelles :
  [`ATLAS-GEOMETRIES-ARCHITECTURE.md`](ATLAS-GEOMETRIES-ARCHITECTURE.md).
- Pipeline, prompts, lot quotidien et sujets d'articles : manifeste et feuille de
  route du comité dans `../aleaquant-editorial-agents/docs/`.
- B3, SIMD, bitplanes et évolutions du moteur HPC :
  `../../loto-keno-lab/docs/CAPITALISATION-HPC-ATLAS.md`.
- Recherche sur covariance et hypothèses statistiques :
  `docs/research/covariance-positions-ordonnees.md` et les notes associées.

## Traçabilité — reste à traiter après le lot du 2 octobre

Corrections C2/C5, contrôle par preuve, note publique et provenance direct/batch :
réalisées, voir CHANGELOG.md et ARTICLE-TRACEABILITY.md.

- [ ] Compléter à l'ingestion les URL d'archives et les dates de couverture par
  composante/régime ; ne pas les déduire des seuls effectifs historiques.
- [ ] Qualifier la régénération des anciennes fiches pour `F.main.decade_sums` :
  le cache à source inchangée conserve les anciens faits. Prévoir relecture des
  articles dont les empreintes deviennent périmées.
- [ ] Étendre le corpus des paraphrases et le contrôle sémantique claim/preuve ;
  l'appariement lexical n'est pas une certification exhaustive du texte.
- [ ] Distribuer le contrat partagé comme paquet pour retirer le couplage local
  au dépôt voisin ; adapter la projection publique aux articles de fond.
