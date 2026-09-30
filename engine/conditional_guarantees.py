"""Garanties conditionnelles de portefeuilles, sur la composante principale.

Auteur : AleaQuant · Version : 0.1 · Date : 2026-10-01.
Historique : premier vérificateur exhaustif et bornes constructives pour l'Atlas.
TODO : relier séparément Chance/étoiles et les barèmes avant de parler de rang.

Une recherche heuristique peut proposer des grilles ; seul ``verify_wheel``
certifie la condition « x correspondances si y numéros tirés sont dans le pool ».
"""

from itertools import combinations
from math import comb


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} doit être un entier >= {minimum}')
    return value


def _parameters(pool_size, grid_size, hits_in_pool, min_hits):
    p = _integer(pool_size, 'pool_size', 1)
    k = _integer(grid_size, 'grid_size', 1)
    y = _integer(hits_in_pool, 'hits_in_pool', 1)
    x = _integer(min_hits, 'min_hits', 1)
    if not x <= min(k, y) or not k <= p or not y <= p:
        raise ValueError('tailles de pool, grille et garantie incompatibles')
    return p, k, y, x


def single_grid_scenarios(pool_size, grid_size, hits_in_pool, min_hits):
    """Nombre de scénarios à y éléments satisfaits par une seule grille de k."""
    p, k, y, x = _parameters(pool_size, grid_size, hits_in_pool, min_hits)
    return sum(comb(k, j) * comb(p-k, y-j)
               for j in range(x, min(k, y)+1) if 0 <= y-j <= p-k)


def counting_lower_bound(pool_size, grid_size, hits_in_pool, min_hits):
    """Borne nécessaire du nombre de grilles ; elle ne prouve pas l'optimalité."""
    p, k, y, x = _parameters(pool_size, grid_size, hits_in_pool, min_hits)
    covered = single_grid_scenarios(p, k, y, x)
    if covered == 0:
        raise ValueError('aucune grille ne peut satisfaire cette garantie')
    total = comb(p, y)
    return (total + covered - 1) // covered


def verify_wheel(pool, grids, hits_in_pool, *, max_scenarios=100_000):
    """Vérifie tous les scénarios du pool et renvoie le pire cas observable.

    ``worst_best_hits >= x`` certifie « x if hits_in_pool of len(pool) » pour
    les numéros de la composante principale. Aucun rang de gain n'est inféré.
    """
    values = tuple(pool)
    if not values or any(type(v) is not int or v <= 0 for v in values) or len(set(values)) != len(values):
        raise ValueError('pool invalide')
    values = tuple(sorted(values))
    y = _integer(hits_in_pool, 'hits_in_pool', 1)
    if y > len(values):
        raise ValueError('hits_in_pool dépasse le pool')
    limit = _integer(max_scenarios, 'max_scenarios', 1)
    total = comb(len(values), y)
    if total > limit:
        raise ValueError(f'{total} scénarios dépassent la limite {limit}')
    pool_set = set(values)
    blocks = []
    for grid in grids:
        block = tuple(grid)
        if not block or any(type(v) is not int for v in block) or len(set(block)) != len(block):
            raise ValueError('grille invalide')
        if not set(block) <= pool_set:
            raise ValueError('grille hors du pool')
        blocks.append(frozenset(block))
    if not blocks or len({tuple(sorted(b)) for b in blocks}) != len(blocks):
        raise ValueError('portefeuille vide ou grilles répétées')
    k = len(blocks[0])
    if any(len(b) != k for b in blocks):
        raise ValueError('tailles de grille différentes')

    worst = k + 1
    witness = None
    minimum_counts = [len(blocks)] * (k + 1)
    for scenario in combinations(values, y):
        scenario_set = set(scenario)
        hits = [len(block & scenario_set) for block in blocks]
        best = max(hits)
        if best < worst:
            worst, witness = best, scenario
        for threshold in range(1, k + 1):
            count = sum(h >= threshold for h in hits)
            minimum_counts[threshold] = min(minimum_counts[threshold], count)
    return {
        'schema': 'aleaquant-conditional-guarantee-v1',
        'pool_size': len(values), 'grid_size': k, 'grid_count': len(blocks),
        'hits_in_pool': y, 'scenarios': total,
        'worst_best_hits': worst, 'worst_case': list(witness),
        'minimum_grids_at_least_hits': {str(x): minimum_counts[x] for x in range(1, k + 1)},
        'method': 'exhaustive',
    }


def greedy_upper_bound(pool_size, grid_size, hits_in_pool, min_hits,
                       *, max_candidates=5_000, max_scenarios=100_000):
    """Construit une roue canonique certifiée, sans prétendre au minimum global."""
    p, k, y, x = _parameters(pool_size, grid_size, hits_in_pool, min_hits)
    candidate_limit = _integer(max_candidates, 'max_candidates', 1)
    scenario_limit = _integer(max_scenarios, 'max_scenarios', 1)
    candidate_count, scenario_count = comb(p, k), comb(p, y)
    if candidate_count > candidate_limit or scenario_count > scenario_limit:
        raise ValueError('recherche dépassant la limite explicite')
    pool = tuple(range(1, p + 1))
    candidates = list(combinations(pool, k))
    scenarios = list(combinations(pool, y))
    masks = []
    for candidate in candidates:
        block = set(candidate)
        masks.append(sum(1 << i for i, scenario in enumerate(scenarios)
                         if len(block.intersection(scenario)) >= x))
    remaining = (1 << scenario_count) - 1
    selected = []
    while remaining:
        choice = max(range(candidate_count), key=lambda i: (masks[i] & remaining).bit_count())
        if not masks[choice] & remaining:
            raise AssertionError('aucun candidat ne couvre le scénario restant')
        selected.append(choice)
        remaining &= ~masks[choice]
    # Retirer les grilles devenues redondantes après les choix suivants.
    for choice in tuple(reversed(selected)):
        covered = 0
        for other in selected:
            if other != choice:
                covered |= masks[other]
        if covered == (1 << scenario_count) - 1:
            selected.remove(choice)
    grids = [list(candidates[i]) for i in selected]
    proof = verify_wheel(pool, grids, y, max_scenarios=scenario_limit)
    if proof['worst_best_hits'] < x:
        raise AssertionError('la roue construite ne satisfait pas la garantie')
    return {
        'pool_size': p, 'grid_size': k, 'hits_in_pool': y, 'min_hits': x,
        'lower_bound': counting_lower_bound(p, k, y, x),
        'upper_bound': len(grids), 'grids': grids,
        'proof': proof, 'optimality_proven': False, 'method': 'greedy-set-cover',
    }
