"""Résout exactement une petite roue conditionnelle de la composante principale.

Auteur : AleaQuant · Version : 0.1 · Date : 2026-10-01.
Historique : pilote MILP pour la frontière taille du pool / garantie / grilles.
TODO : mesurer l'échelle admissible par jeu et archiver d'autres cohortes utiles.

SciPy/HiGHS est une dépendance facultative de recherche, absente du site publié.
L'objectif minimise le nombre de grilles ; chaque scénario de y numéros dans
le pool doit recouper au moins une grille en x numéros. La solution retournée
est revérifiée par le moteur déterministe indépendant du solveur.
"""

import argparse
from hashlib import sha256
from itertools import combinations
import json
from math import comb
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from conditional_guarantees import (  # noqa: E402
    counting_lower_bound, single_grid_scenarios, verify_wheel,
)


def solve(pool_size, grid_size, hits_in_pool, min_hits, *, time_limit=30,
          max_candidates=5_000, max_scenarios=100_000):
    import numpy as np
    import scipy
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import csr_matrix

    # Ces validations précèdent toute construction de matrice importante.
    single_grid_scenarios(pool_size, grid_size, hits_in_pool, min_hits)
    if type(time_limit) not in (int, float) or time_limit <= 0:
        raise ValueError('time_limit doit être positif')
    n_candidates = comb(pool_size, grid_size)
    n_scenarios = comb(pool_size, hits_in_pool)
    if n_candidates > max_candidates or n_scenarios > max_scenarios:
        raise ValueError('problème dépassant la limite explicite')
    pool = tuple(range(1, pool_size + 1))
    candidates = list(combinations(pool, grid_size))
    scenarios = list(combinations(pool, hits_in_pool))
    rows, columns = [], []
    for j, grid in enumerate(candidates):
        chosen = set(grid)
        for i, scenario in enumerate(scenarios):
            if len(chosen.intersection(scenario)) >= min_hits:
                rows.append(i)
                columns.append(j)
    matrix = csr_matrix((np.ones(len(rows)), (rows, columns)),
                        shape=(n_scenarios, n_candidates))
    start = perf_counter()
    result = milp(np.ones(n_candidates), integrality=np.ones(n_candidates),
                  bounds=Bounds(0, 1),
                  constraints=LinearConstraint(matrix, 1, np.inf),
                  options={'time_limit': float(time_limit), 'mip_rel_gap': 0})
    elapsed = perf_counter() - start
    selected = ([list(candidates[i]) for i, value in enumerate(result.x) if value > 0.5]
                if result.x is not None else [])
    proof = verify_wheel(pool, selected, hits_in_pool,
                         max_scenarios=max_scenarios) if selected else None
    if proof and proof['worst_best_hits'] < min_hits:
        raise AssertionError('le candidat du solveur échoue à la vérification exhaustive')
    dual_bound = float(result.mip_dual_bound) if result.x is not None else None
    optimal = (result.status == 0 and proof is not None
               and abs(dual_bound - len(selected)) < 1e-8)
    grid_bytes = json.dumps(selected, separators=(',', ':')).encode()
    return {
        'schema': 'aleaquant-conditional-wheel-search-v1',
        'pool_size': pool_size, 'grid_size': grid_size,
        'hits_in_pool': hits_in_pool, 'min_hits': min_hits,
        'candidate_grids': n_candidates, 'conditional_scenarios': n_scenarios,
        'counting_lower_bound': counting_lower_bound(pool_size, grid_size,
                                                      hits_in_pool, min_hits),
        'solver': 'scipy-milp-highs', 'scipy_version': scipy.__version__,
        'solver_status': int(result.status), 'solver_message': result.message,
        'solver_lower_bound': dual_bound,
        'solver_gap': (float(result.mip_gap) if result.x is not None else None),
        'elapsed_seconds': round(elapsed, 3),
        'optimality_proven_by_solver': optimal,
        'minimum_grid_count': len(selected) if optimal else None,
        'candidate_grid_count': len(selected) if selected else None,
        'grids_sha256': sha256(grid_bytes).hexdigest(),
        'source_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'grids': selected, 'verification': proof,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pool-size', type=int, required=True)
    parser.add_argument('--grid-size', type=int, required=True)
    parser.add_argument('--hits-in-pool', type=int, required=True)
    parser.add_argument('--min-hits', type=int, required=True)
    parser.add_argument('--time-limit', type=float, default=30)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = solve(args.pool_size, args.grid_size, args.hits_in_pool,
                   args.min_hits, time_limit=args.time_limit)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
