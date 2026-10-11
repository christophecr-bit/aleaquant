"""Portfolio definitions extend the common Atlas dictionary, never replace it."""
from collections import Counter
from itertools import combinations
from math import sqrt

VERSION = 'portfolio-metrics-1.0'


def entry(key, name, definition, unit, direction, method='exact'):
    return {'id':'portfolio.'+key+'@v1', 'group':'portfolio', 'name':name,
            'version':1, 'scope':'portfolio', 'definition':definition, 'unit':unit,
            'direction':direction, 'evidence_method':method, 'evaluator_version':VERSION}


REGISTRY = [
    entry('distinct_pairs','Paires couvertes','Nombre de sous-ensembles distincts de deux numéros présents dans au moins une grille ; dénominateur C(50,2)=1225.','count','max'),
    entry('distinct_triples','Triplets couverts','Nombre de sous-ensembles distincts de trois numéros présents dans au moins une grille ; dénominateur C(50,3)=19600.','count','max'),
    entry('mean_number_overlap','Intersection moyenne des numéros','Moyenne des |A∩B| sur les paires non ordonnées de grilles ; indéfinie pour une seule grille. Ne départage pas les portefeuilles de fréquences individuelles identiques.','numbers','min'),
    entry('max_number_overlap','Intersection maximale des numéros','Maximum des |A∩B| entre deux grilles ; indéfini pour une seule grille.','numbers','min'),
    entry('number_overlap_square_sum','Somme des intersections au carré, numéros','Somme de |A∩B|² sur les paires de grilles. minimize_overlap multiplie ce terme par son poids numbers ; concentration préfère ce même terme avec son poids positif.','sum of squared counts','profile_defined'),
    entry('star_overlap_square_sum','Somme des intersections au carré, étoiles','Somme de |S_A∩S_B|² sur les paires de grilles, pénalisée par minimize_overlap.stars.','sum of squared counts','min'),
    entry('number_frequency_sd','Dispersion des fréquences des numéros','Écart-type population des occurrences sur les 50 numéros, y compris ceux absents. Le mode greedy pénalise les écarts au carré dans le pool ; prototype_greedy pénalise la somme des occurrences courantes du candidat.','count','min'),
    entry('star_frequency_sd','Dispersion des fréquences des étoiles','Écart-type population des occurrences sur les 12 étoiles, zéros inclus. Le mode greedy pénalise la dispersion dans le pool ; prototype_greedy pénalise les occurrences courantes des étoiles du candidat.','count','min'),
    entry('distinct_star_pairs','Paires d’étoiles couvertes','Nombre de combinaisons distinctes d’étoiles jouées, sur C(12,2)=66.','count','max'),
    entry('any_prize_probability','Fréquence d’au moins une grille gagnante','Probabilité qu’au moins une même grille atteigne un rang gagnant standard EuroMillions : au moins deux numéros, ou un numéro et deux étoiles. IC95 Wilson, échantillon indépendant ; aucun montant ni remboursement évalué.','probability','descriptive','monte_carlo'),
    entry('multiple_prizes_probability','Fréquence de gains simultanés','Probabilité d’au moins deux grilles gagnantes sur le même tirage ; même règle de gain et échantillon partagé. IC95 Wilson.','probability','descriptive','monte_carlo'),
    entry('jackpot_probability','Probabilité exacte du jackpot','Pour m grilles distinctes, m/[C(50,5)×C(12,2)]. Calcul exact ; le MC ne sert pas à estimer cet événement rare.','probability','descriptive'),
    entry('number_overlap_distribution','Distribution des intersections de numéros','Vecteur de six effectifs pour les intersections de taille 0 à 5, sur les paires non ordonnées de grilles. La somme vaut C(m,2).','count vector','descriptive'),
    entry('star_overlap_distribution','Distribution des intersections d’étoiles','Vecteur de trois effectifs pour les intersections de taille 0 à 2, sur les paires non ordonnées de grilles. La somme vaut C(m,2).','count vector','descriptive'),
    entry('number_frequencies','Occurrences des numéros','Vecteur des occurrences des numéros 1 à 50, zéros inclus ; la somme vaut 5m. Le pool déclaré indique quelles valeurs sont admissibles.','count vector','descriptive'),
    entry('star_frequencies','Occurrences des étoiles','Vecteur des occurrences des étoiles 1 à 12, zéros inclus ; la somme vaut 2m. À distinguer du nombre de paires d’étoiles distinctes.','count vector','descriptive'),
    entry('at_least_3_numbers_probability','Fréquence d’au moins trois numéros','Probabilité qu’au moins une grille possède au moins trois numéros tirés, indépendamment de ses étoiles ; IC95 Wilson sur un échantillon déclaré.','probability','descriptive','monte_carlo'),
    entry('at_least_4_numbers_probability','Fréquence d’au moins quatre numéros','Probabilité qu’au moins une grille possède au moins quatre numéros tirés, indépendamment de ses étoiles ; IC95 Wilson sur un échantillon déclaré.','probability','descriptive','monte_carlo'),
    entry('mean_winning_grids','Nombre moyen de grilles gagnantes','Moyenne empirique des grilles atteignant un rang gagnant standard sur les tirages simulés. Un nombre de grilles gagnantes ne mesure aucun montant ni bénéfice. L’espérance analytique dépend seulement du nombre de grilles valides.','winning grids per draw','descriptive','monte_carlo'),
]


def metric_values(grids, geometry, simulation=None):
    stars = Counter(v for g in grids for v in g[1])
    mean = 2*len(grids)/12
    raw = {
        'distinct_pairs':geometry['coverage'][2]['covered'],
        'distinct_triples':geometry['coverage'][3]['covered'],
        'mean_number_overlap':geometry['overlap_mean'],
        'max_number_overlap':geometry['overlap_max'],
        'number_overlap_square_sum':sum(len(set(a[0])&set(b[0]))**2 for a,b in combinations(grids,2)),
        'star_overlap_square_sum':sum(len(set(a[1])&set(b[1]))**2 for a,b in combinations(grids,2)),
        'number_frequency_sd':geometry['occurrence_sd'],
        'star_frequency_sd':sqrt(sum((stars.get(v,0)-mean)**2 for v in range(1,13))/12),
        'distinct_star_pairs':geometry['second']['distinct_combinations'],
        'number_overlap_distribution':geometry['overlap_hist'],
        'star_overlap_distribution':[sum(len(set(a[1])&set(b[1]))==i for a,b in combinations(grids,2)) for i in range(3)],
        'number_frequencies':[sum(i in g[0] for g in grids) for i in range(1,51)],
        'star_frequencies':[stars.get(i,0) for i in range(1,13)],
    }
    if simulation:
        raw['any_prize_probability']=simulation['metrics']['any_prize']['probability']
        raw['multiple_prizes_probability']=simulation['metrics']['multiple_prizes']['probability']
        raw['at_least_3_numbers_probability']=simulation['metrics']['at_least_3_numbers']['probability']
        raw['at_least_4_numbers_probability']=simulation['metrics']['at_least_4_numbers']['probability']
        raw['mean_winning_grids']=simulation['mean_winning_grids']
    return {'portfolio.'+k+'@v1':v for k,v in raw.items()}
