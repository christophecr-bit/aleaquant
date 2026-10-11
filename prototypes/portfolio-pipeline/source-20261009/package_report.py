from pathlib import Path
import json,html,math,zipfile
r=Path(__file__).parent; d=json.loads((r/'results.json').read_text()); ps=d['profiles']
def pct(x):return f'{100*x:.2f} %'
rows=''
for p in ps:
 e=p['exact'];m=p['simulation']['metrics'];rows+=f"<tr><td><a href='#{p['id']}'>{p['family']} {p['budget_eur']:g} €</a></td><td>{len(p['grids'])}</td><td>{len(p['pool_numbers'])} / {len(p['pool_stars'])}</td><td>{pct(m['any_prize']['probability'])}</td><td>{pct(m['at_least_3_numbers']['probability'])}</td><td>{e['mean_number_overlap']:.2f} / {e['max_number_overlap']}</td><td>{e['distinct_triples']}</td></tr>"
body=''
for p in ps:
 cert=p['certificate'];e=p['exact'];met=p['simulation']['metrics']; gs=''.join(f"<tr><td>{i}</td><td>{' · '.join(f'{n:02}' for n in g['numbers'])}</td><td>{' · '.join(f'{n:02}' for n in g['stars'])}</td></tr>" for i,g in enumerate(p['grids'],1))
 if cert['method']=='exhaustive_enumeration':
  proofs=[]
  for s,n in cert['minimum_best_numbers_by_required_stars'].items():
   proofs.append(f"{n} numéros + au moins {s} étoile(s) sur une même grille" if n>=0 else f"aucune garantie pour {s} étoiles")
  certificate=f"<p><b>Condition :</b> {cert['condition']} Vérification de {cert['cases']:,} cas. Garanties distinctes : {' ; '.join(proofs)}. La probabilité que cette condition soit remplie est {pct(cert['condition_probability'])}.</p>"
 else:certificate='<p>Aucune garantie conditionnelle certifiée. L’absence de certification ne constitue pas une preuve d’impossibilité.</p>'
 intervals=''.join(f"<li>{label} : {pct(met[key]['probability'])} ; intervalle à 95 % [{pct(met[key]['ci95_wilson'][0])} – {pct(met[key]['ci95_wilson'][1])}]</li>" for key,label in [('any_prize','Au moins un gain'),('multiple_prizes','Au moins deux grilles gagnantes'),('at_least_3_numbers','Au moins trois numéros sur une grille'),('at_least_4_numbers','Au moins quatre numéros sur une grille')])
 body+=f"<section id='{p['id']}'><h2>{p['family']} — {p['budget_eur']:g} €</h2><p>Pool numéros : {p['pool_numbers']}<br>Pool étoiles : {p['pool_stars']}</p>{certificate}<ul>{intervals}</ul><p>Paires de numéros distinctes : {e['distinct_pairs']} / {math.comb(len(p['pool_numbers']),2)} dans le pool. Triplets : {e['distinct_triples']} / {math.comb(len(p['pool_numbers']),3)}. Paires d’étoiles : {e['distinct_star_pairs']} / {math.comb(len(p['pool_stars']),2)}.</p><p>Probabilité exacte du jackpot : 1 sur {1/e['jackpot_probability']:,.0f}. Grilles gagnantes moyennes par tirage : {p['simulation']['mean_winning_grids']:.3f}, valeur théorique {p['simulation']['theoretical_mean_winning_grids']:.3f}.</p><table><thead><tr><th>Grille</th><th>Numéros</th><th>Étoiles</th></tr></thead><tbody>{gs}</tbody></table></section>"
page=f'''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aleaquant — Portefeuilles et pipeline</title><style>body{{font:16px/1.6 system-ui,sans-serif;background:#f6f7fa;color:#172236;max-width:1100px;margin:32px auto;padding:0 20px}}h1{{font-size:32px}}h2{{font-size:24px}}section,.intro{{background:white;padding:24px;margin:24px 0;border-radius:12px;border:1px solid #dce2ec}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #e2e7ee}}th{{background:#eaf0f7}}a{{color:#17569b}}.scroll{{overflow-x:auto}}.note{{border-left:4px solid #d89921;padding:12px;background:#fff7e5}}@media print{{body{{background:white;font-size:11px}}section{{break-before:page}}}}</style><h1>Aleaquant · bibliothèque EuroMillions</h1><p>9 octobre 2026 · prototype 0.1 · six portefeuilles alternatifs de 45 à 55 €</p><div class="intro"><p>Choisir un portefeuille parmi ces variantes. Chaque liste contient des grilles simples à 2,50 €, hors Étoile+. Aucun achat n’a été effectué.</p><p class="note"><b>Au moins un gain ne signifie pas rembourser la mise.</b> Les probabilités concernent les rangs EuroMillions uniquement, sans My Million. Les montants de gains et la rentabilité ne sont pas évalués.</p><div class="scroll"><table><thead><tr><th>Variante</th><th>Grilles</th><th>Pool N / E</th><th>≥ 1 gain</th><th>≥ 3 numéros</th><th>Overlap moyen / max</th><th>Triplets distincts</th></tr></thead><tbody>{rows}</tbody></table></div><p>500 000 tirages uniformes, indépendants de la génération et communs aux six variantes. Intervalles de Wilson à 95 % dans chaque fiche. Les faibles différences ne prouvent pas une supériorité. Les pools diffèrent : ce tableau compare ces constructions précises, pas la valeur intrinsèque des familles.</p><p>Les Spread ont un recouvrement maximal de 1 numéro, vérifié exactement ; ils favorisent ici la fréquence d’un gain. Complete et Clustered concentrent davantage les grilles gagnantes sur certains tirages. À nombre de grilles distinctes égal, la probabilité du jackpot est identique.</p><p>Numéros choisis par graine reproductible, sans historique ni prédiction. Optimisation heuristique sans preuve d’optimalité.</p></div>{body}<section><h2>Cadre de paramétrage et lien avec l’Atlas</h2><p>Profils versionnés → validation des contraintes → génération → mesures exactes → évaluation indépendante → export Atlas. Consulter README.md pour le contrat, les limites et les commandes.</p><p>Le dictionnaire Atlas existant décrit des métriques de grille. Proposition : y ajouter un espace portfolio.* pour les métriques entre grilles, avec définition, portée, sens d’optimisation et méthode de preuve. Les identifiants internes actuels de l’Atlas restent à raccorder.</p><p>Sources : <a href="https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/comment-jouer">règles et prix FDJ</a> ; <a href="https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/gains">rangs de gains FDJ</a>. Conditions retenues : 5/50, 2/12, gain si au moins deux numéros ou un numéro et deux étoiles.</p></section></html>'''
(r/'catalogue.html').write_text(page)
readme='''# Aleaquant — Pipeline de portefeuilles 0.1

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
'''
(r/'README.md').write_text(readme)
# Independent analytic check of the complete construction.
a=sum(math.comb(6,j)*math.comb(44,5-j)/math.comb(50,5) for j in range(2,6))+math.comb(6,1)*math.comb(44,4)/math.comb(50,5)*3/66
ci=ps[0]['simulation']['metrics']['any_prize']['ci95_wilson'];assert ci[0]<a<ci[1]
checks={'grids':sum(len(p['grids']) for p in ps),'complete_any_prize_exact':a,'complete_simulation_ci95':ci,'analytic_check_passed':True,'budgets':[p['budget_eur'] for p in ps]}
(r/'validation.json').write_text(json.dumps(checks,indent=2))
with zipfile.ZipFile(r.parent/'aleaquant_pipeline_2026-10-09.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['build.py','profiles.json','results.json','atlas.json','catalogue.html','README.md','package_report.py','validation.json']:z.write(r/name,name)
print(json.dumps(checks));print('archive ready')
