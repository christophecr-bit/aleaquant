"""Géométrie descriptive partagée des portefeuilles de l'Atlas.

Version : 0.1 | Date : 2026-10-09 | Auteur : AleaQuant
Historique : extraction du calcul publié dans build_data.py, sans changer ses
valeurs ni ses champs pour les portefeuilles existants.
TODO : étendre le contrat aux composantes supplémentaires si un jeu le demande.

Les grilles sont des listes de composantes : [[numéros], [étoiles/Chance]] ou
[[numéros]]. Leur validité relève du lecteur de catalogue. Sans paire de
grilles, les overlaps moyen et maximal sont inconnus (None), et l'histogramme
principal contient zéro paire.
"""
from collections import Counter
from itertools import combinations
from math import comb

import numpy as np


def portfolio_geometry(grids, domain):
    """Mesures exactes de couverture et intersections, dispersion descriptive."""
    if not grids:
        raise ValueError('un portefeuille doit contenir au moins une grille')
    sets = [frozenset(g[0]) for g in grids]
    k = len(grids[0][0])
    inter = [len(a & b) for a, b in combinations(sets, 2)]
    occ = Counter(v for s in sets for v in s)
    cov = {}
    for t in (2, 3):
        c = Counter(sub for g in grids for sub in combinations(sorted(g[0]), t))
        cov[t] = {'covered': len(c), 'possible': comb(domain, t),
                  'collisions': sum(comb(m, 2) for m in c.values())}
    out = {'grids': len(grids), 'union': len(set().union(*sets)),
           'overlap_mean': sum(inter) / len(inter) if inter else None,
           'overlap_max': max(inter) if inter else None,
           'overlap_hist': [inter.count(i) for i in range(k + 1)],
           'occurrence_sd': float(np.std([occ.get(v, 0) for v in range(1, domain + 1)])),
           'coverage': cov}
    if len(grids[0]) > 1:  # étoiles (EuroMillions) ou numéro Chance (Loto)
        second = [frozenset(g[1]) for g in grids]
        inter2 = [len(a & b) for a, b in combinations(second, 2)]
        out['second'] = {'union': len(set().union(*second)),
                         'overlap_mean': sum(inter2) / len(inter2) if inter2 else None,
                         'overlap_max': max(inter2) if inter2 else None,
                         'distinct_combinations': len({tuple(sorted(x)) for x in second})}
    return out
