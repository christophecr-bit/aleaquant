"""Lois exactes des métriques EuroMillions par énumération complète.

C(50,5) = 2 118 760 combinaisons de numéros et C(12,2) = 66 paires d'étoiles.
Calcul unique (environ une minute) : le résultat ne dépend que des définitions
de patterns.py, dont le SHA-256 est enregistré. À relancer seulement si ce SHA
change. Aucune simulation, aucun historique.
"""
from itertools import combinations
from math import comb
import time

from common import (DATA, MAIN_CAT, MAIN_FIELDS, PATTERNS, STAR_FIELDS, ENGINE_VERSION,
                    key, load_patterns, sha256_file, write_json)


def build():
    patterns = load_patterns()
    started = time.time()
    main = {f: {} for f in MAIN_FIELDS + MAIN_CAT}
    for grid in combinations(range(1, 51), 5):
        p = patterns.main_pattern(grid)
        for field, law in main.items():
            k = key(p[field])
            law[k] = law.get(k, 0) + 1
    stars = {f: {} for f in STAR_FIELDS}
    for pair in combinations(range(1, 13), 2):
        p = patterns.stars_pattern(pair)
        for field, law in stars.items():
            k = key(p[field])
            law[k] = law.get(k, 0) + 1
    result = {
        'schema': 'aleaquant-exact-laws-v1', 'engine': ENGINE_VERSION,
        'rule_id': 'euromillions-50-12-v1',
        'patterns_sha256': sha256_file(PATTERNS),
        'method': 'exhaustive enumeration, no sampling',
        'main_total': comb(50, 5), 'stars_total': comb(12, 2),
        'main': main, 'stars': stars,
        'seconds': round(time.time() - started, 1),
    }
    for field, law in main.items():
        assert sum(law.values()) == comb(50, 5), field
    write_json(DATA / 'exact_laws.json', result)
    return result


if __name__ == '__main__':
    r = build()
    print('lois exactes écrites', r['seconds'], 's', r['patterns_sha256'][:12])
