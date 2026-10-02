# Dette technique active — 2 octobre 2026

Auteur : AleaQuant · v2.4

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
- [ ] **Publier les archives Keno 20/70 à la demande** : les 333 pages du régime
  actif 16/56 sont publiées et vérifiées (DEPLOYMENTS.md, 2 octobre). Servir les
  19 133 anciens tirages 20/70 avec un index
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

- [ ] **Outiller l’exploitation autonome des batchs (PB-014)** : raccorder un
  module d’administration privé à la console existante, en complément du suivi
  PB-011. Réutiliser les commandes et configurations canoniques ; ne pas dupliquer
  les calculs. Premier périmètre : récupération des trois jeux, faits, profils et
  reconstruction locale des pages, avec filtres jeu/régime/période/tirages.
  Prévoir une file persistante exécutée sur le Mac, un identifiant par exécution,
  paramètres et versions journalisés, états/progression, logs et rapport final.
  Distinguer reprise depuis un checkpoint et relance idempotente ; exposer les
  capacités réelles de chaque batch, sans promettre une reprise universelle.
  Partager les verrous avec launchd, empêcher les doubles lancements, prévoir
  arrêt propre et récupération après veille/redémarrage. Le navigateur ne doit
  pas porter la durée de vie du calcul ; afficher si le Mac est indisponible.
  Avant remplacement : contrôles, comparaison, sauvegarde et impact sur les SHA
  approuvés. Accès authentifié, actions prédéfinies avec paramètres validés et
  secrets côté serveur ; aucun terminal arbitraire exposé. Lancement des longs
  calculs HPC et campagnes LLM (budget explicite) à cadrer dans un second lot.
  Validation attendue : lancer un lot témoin de chaque jeu sans terminal, simuler
  échec/interruption/double lancement et vérifier la protection d’un article
  approuvé. Déploiement et approbation éditoriale restent des actions distinctes.
- [ ] **Rendre le déploiement reproductible** : vérifier le lien GitHub–Cloudflare,
  créer les environnements recette/production prévus dans
  [`CI-STAGING-PRODUCTION.md`](CI-STAGING-PRODUCTION.md), séparer les secrets et
  exécuter les contrôles/tests avant déploiement. Le flux actuellement vérifié
  reste manuel (`wrangler deploy`, puis `git push`).
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

### Qualification du rattrapage — 2 octobre 2026

Le rattrapage a été exécuté sur trois fiches : anciennes valeurs inchangées,
seule la métrique sommes par dizaine s'ajoute. Le faux positif « sous-total »
singulier est corrigé et testé (voir VALIDATION-RECALCUL-20261002.md).
Reste à généraliser le rattrapage, puis à décider du lancement de la campagne.
Fiches, puces et textes ont des validations distinctes : aucune puce n'est exigée.
La reprise automatique des remarques humaines par le Writer reste ouverte.

### Rattrapage global qualifié — 2 octobre 2026

Le recalcul des faits des trois jeux est terminé et comparé intégralement :
29 124 fiches, 650 775 faits antérieurs inchangés. Le point « généraliser le
rattrapage » est réalisé. Une seule bascule reste suspendue : EM-2011053 jusqu'à
revalidation de son article approuvé. Sa nouvelle fiche est déjà calculée.
Reste à rendre pérenne la sélection de snapshots de faits par version approuvée,
pour qu'un futur recalcul ne retire pas silencieusement un article du rendu.
