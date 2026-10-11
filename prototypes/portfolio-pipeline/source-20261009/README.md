# Aleaquant — Pipeline de portefeuilles 0.1

Prototype du 9 octobre 2026, indépendant du dépôt existant. Six portefeuilles évalués et catalogue.html prêt à consulter. Aucun raccordement au Site ni au dépôt n’a été effectué.

## Exécution

Python 3.10+ et NumPy (validation effectuée avec NumPy 2.3.5).

    python build.py --config profiles.json --output .
    python package_report.py

Lancer ces commandes depuis le dossier extrait. Le pipeline ne lit aucun historique et ne passe aucun ordre de jeu.

## Contrat de paramétrage

Le fichier profiles.json est l’entrée exécutable du prototype. Champs : schema_version, game, unit_price_eur, pool_seed, evaluation et profiles.
Chaque profil contient id, family, constraints, objectives et search.
Contraintes exécutées : grid_count, budget_max_eur, pool_number_count, pool_star_count, unique_grids. Le jeu fixe 5 numéros parmi 50 et 2 étoiles parmi 12. Le coût est calculé et comparé au plafond.
Objectifs pondérés exécutés : maximize_distinct_triples, maximize_distinct_pairs, balance_number_frequency, balance_star_frequency et minimize_overlap.
minimize_overlap pénalise ici la somme des carrés des intersections de numéros entre le candidat et les grilles déjà sélectionnées. C’est un objectif souple. Une contrainte dure future devra être nommée max_pairwise_overlap et vérifiée indépendamment.
Recherche exécutée : candidates_per_step et seed. Balanced et Spread utilisent la même méthode avec des pools et poids différents ; Clustered fixe un noyau de trois numéros ; Complete énumère toutes les combinaisons du pool.
La somme des intersections est fixée par les fréquences individuelles : l’overlap moyen seul ne suffit pas à départager deux constructions dont les fréquences sont identiques. Conserver distribution, maximum et redondances d’ordre supérieur.

## Score glouton exécuté

Pour chaque ajout, tester candidates_per_step candidats aléatoires valides et retenir le meilleur : poids triplets × nouveaux triplets + poids paires × nouvelles paires − poids fréquences numéros × somme des fréquences actuelles des numéros du candidat − poids fréquences étoiles × somme des fréquences étoiles − poids overlap × somme des intersections au carré. Pas d’optimisation de la simulation ; évaluation après gel des grilles. Le score n’est pas une probabilité de gain.

## Pipeline et états

1. Charger et valider le profil (identifiants uniques, domaine, budget, capacité combinatoire).
2. Construire une population initiale. Prototype : une construction par profil.
3. Vérifier grilles, doublons et coût ; compter paires, triplets et intersections exactement.
4. Pour les pools de 15 numéros ou moins, énumérer tous les tirages 5+2 internes au pool. Pour chaque seuil d’étoiles, calculer le minimum, sur les tirages, du meilleur nombre de correspondances sur une même grille. -1 signifie aucune grille satisfaisant ce seuil d’étoiles pour au moins un cas. 0+2 n’est pas un rang gagnant EuroMillions sans option.
5. Simuler 500 000 tirages uniformes communs, avec graine séparée. Produire événements, intervalles et nombre moyen de grilles gagnantes. Ne pas estimer les événements rares comme le jackpot par Monte-Carlo ; utiliser le calcul exact.
6. Exporter results.json, atlas.json puis catalogue.html.

États à introduire dans l’intégration : draft, invalid, feasible, evaluated, certified, search_exhausted, proven_infeasible. Le prototype échoue par exception pour une entrée invalide ; aucune recherche interrompue ne prouve une impossibilité.

## Atlas et graphe

La capture publiée d’AleaQuant consultée présente 33 définitions de métriques de grilles (numéros et étoiles). Elle ne fournit pas de schéma technique du dépôt. Ne pas inventer leurs identifiants internes.
Proposition de registre : metric_id, version, scope (grid/portfolio/conditional/unconditional), definition, unit, direction, evaluator_version, evidence_method. Introduire portfolio.mean_number_overlap, portfolio.max_number_overlap, portfolio.distinct_pairs, portfolio.distinct_triples, portfolio.distinct_star_pairs, portfolio.any_prize_probability. Ne pas utiliser les propriétés visuelles ou arithmétiques d’une grille comme preuve prédictive.
Le contrat atlas.json est PROPOSÉ, non raccordé : nodes contiennent les individus et leurs résultats ; edges recevront mutation_of et crossover_of. Les individus initiaux n’ont aucun parent. La relation generated_from doit relier un individu à une version de profil lorsque les nœuds de profils seront ajoutés. Les familles servent de classification, pas de parent biologique.
Pour une version durable : identifiants de contenu, empreinte des grilles canoniques, version du moteur, empreinte de configuration, protocole d’évaluation, dates, origine des parents et mutations exactes. Un même individu peut avoir plusieurs EvaluationRun indépendants ; les preuves doivent être liées à son empreinte.

## Prochaines étapes d’implémentation

- Raccorder les définitions et métriques existantes de l’Atlas, sans créer un second dictionnaire divergent.
- Ajouter un schéma JSON strict, messages d’erreurs et tests de faisabilité ; remplacer les assertions du prototype avant un usage de production. Ne pas exécuter avec python -O.
- Ajouter les listes explicites de pools, contraintes de garantie demandée et max_pairwise_overlap. Elles ne sont PAS encore prises en entrée par ce prototype.
- Ajouter mutation, croisement, réparation, sélection multiobjectif et préservation de diversité ; à chaque enfant, revalider les contraintes et recertifier les garanties.
- Ajouter budgets de calcul, checkpoints, reprise et comparaison à plusieurs graines. Pour une reproductibilité bit à bit, figer Python/NumPy et le moteur ; la graine seule ne suffit pas entre versions.
- Séparer échantillons de sélection et de test final si la simulation devient une fonction d’optimisation.
- Vérifier la sémantique exacte de garantie : nombre de bons numéros et étoiles DANS le pool, puis rang minimal conjoint sur UNE grille.
- Cataloguer familles × budgets, sans classement unique confondant probabilités de petits gains, remboursement et jackpot.

## Interprétation

Les variantes sont des alternatives : leurs budgets ne se cumulent pas pour la comparaison. Un gain n’est pas un bénéfice. Aucun montant de gain, remboursement de mise, My Million ou Étoile+ n’est simulé. Les garanties sont conditionnelles, ne sont pas des garanties de gain inconditionnelles. Les poids heuristiques ne sont pas des preuves d’optimalité. La définition d’un pool est symétrique sous renommage des numéros.

Sources officielles : https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/comment-jouer et https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/gains
