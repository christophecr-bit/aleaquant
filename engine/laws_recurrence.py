"""Lois marginales exactes pour les grands régimes Keno, sans énumérer les grilles.

Chaque transition compte des sous-ensembles, avec des entiers Python arbitrairement
grands. Les champs non couverts ne sont pas émis : une loi manquante vaut mieux qu'une
rareté inventée. `tests/test_laws_recurrence.py` confronte toutes ces lois à une
énumération exhaustive sur de petits domaines avant la construction 16/56 et 20/70.
"""
# Version: 0.2.0 · Updated: 2026-10-01 · Author: AleaQuant
# History: 0.2.0 adds the validated Metal 16/56 laws to the exact recurrence output.
# TODO (AleaQuant): independently cross-check the full-domain Metal histograms.
import json
from collections import Counter, defaultdict
from fractions import Fraction
from math import comb, factorial
from pathlib import Path

from common import key


def _c(n, k):
    return comb(n, k) if 0 <= k <= n else 0


def _somme(k, n):
    # Après avoir lu les valeurs 1..x, dp[j][s] compte les sous-ensembles de
    # taille j et de somme s. Descendre j interdit de reprendre x deux fois.
    dp = [Counter() for _ in range(k + 1)]
    dp[0][0] = 1
    for x in range(1, n + 1):
        for j in range(min(x, k), 0, -1):
            for s, count in dp[j - 1].items():
                dp[j][s + x] += count
    return dp[k]


def _etendue(k, n):
    # Pour une étendue s : choisir le minimum (n-s choix), puis les k-2
    # points intérieurs parmi s-1. Les deux bornes sont imposées.
    return Counter({s: (n - s) * _c(s - 1, k - 2)
                    for s in range(k - 1, n)})


def _ecart_min(k, n):
    # min_gap >= g <=> après translation de x_i par (i-1)(g-1), on choisit
    # librement k points parmi n-(k-1)(g-1).
    def au_moins(g):
        return _c(n - (k - 1) * (g - 1), k)
    maxi = (n - 1) // (k - 1)
    return Counter({g: au_moins(g) - au_moins(g + 1)
                    for g in range(1, maxi + 1)})


def _ecart_max(k, n):
    # Pour une borne g, dp[j][x] compte les sélections de j points dont le
    # dernier est x et dont tous les écarts valent au plus g. La différence
    # de deux cumuls successifs donne P(max_gap = g).
    def au_plus(g):
        previous = [0] + [1] * n
        for _ in range(2, k + 1):
            prefix = [0]
            for count in previous:
                prefix.append(prefix[-1] + count)
            current = [0] * (n + 1)
            for x in range(1, n + 1):
                current[x] = prefix[x] - prefix[max(1, x - g)]
            previous = current
        return sum(previous)
    out = Counter()
    before = 0
    for g in range(1, n - k + 2):
        now = au_plus(g)
        out[g] = now - before
        before = now
    return out


def _suites(k, n):
    # Une sélection de k points se décompose en r suites maximales de longueurs
    # positives totalisant k. Chaque composition se place de C(n-k+1,r) façons.
    states = [defaultdict(int) for _ in range(k + 1)]
    states[0][(0, 0, 0)] = 1  # (nombre de suites, suites >=2, longueur max)
    for used in range(k):
        for (runs, ge2, longest), ways in states[used].items():
            for length in range(1, k - used + 1):
                states[used + length][(runs + 1, ge2 + (length >= 2),
                                       max(longest, length))] += ways
    consecutive, long_run, runs_ge2 = Counter(), Counter(), Counter()
    for (runs, ge2, longest), compositions in states[k].items():
        ways = compositions * _c(n - k + 1, runs)
        consecutive[k - runs] += ways
        long_run[longest] += ways
        runs_ge2[ge2] += ways
    return consecutive, long_run, runs_ge2


def _hypergeom(k, n, marked):
    return Counter({j: _c(marked, j) * _c(n - marked, k - j)
                    for j in range(max(0, k - (n - marked)), min(k, marked) + 1)})


def _dizaines(k, n):
    tailles = [min(10, n - start + 1) for start in range(1, n + 1, 10)]
    exact, max_same, occupied = Counter(), Counter(), Counter()

    def visit(i, remaining, counts, ways):
        if i == len(tailles):
            if remaining == 0:
                signature = tuple(counts)
                exact[signature] += ways
                max_same[max(signature)] += ways
                occupied[sum(c > 0 for c in signature)] += ways
            return
        available_after = sum(tailles[i + 1:])
        lo, hi = max(0, remaining - available_after), min(tailles[i], remaining)
        for c in range(lo, hi + 1):
            counts.append(c)
            visit(i + 1, remaining - c, counts, ways * comb(tailles[i], c))
            counts.pop()

    visit(0, k, [], 1)
    return exact, max_same, occupied


def _finales(k, n):
    # Les dix finales sont des catégories de tailles inégales lorsque n n'est
    # pas un multiple de 10. On conserve les deux statistiques conjointement.
    tailles = [len(range(d if d else 10, n + 1, 10)) for d in range(10)]
    states = {(0, 0, 0): 1}  # (points choisis, finales occupées, collisions)
    for taille in tailles:
        next_states = defaultdict(int)
        for (used, occupied, collisions), ways in states.items():
            for c in range(0, min(taille, k - used) + 1):
                next_states[(used + c, occupied + (c > 0),
                             collisions + _c(c, 2))] += ways * comb(taille, c)
        states = next_states
    repeated, pairs = Counter(), Counter()
    for (used, occupied, collisions), ways in states.items():
        if used == k:
            repeated[k - occupied] += ways
            pairs[collisions] += ways
    return repeated, pairs


def _progression_complete(k, n):
    # Une progression de k points est identifiée par son pas positif et son
    # premier point ; pour chaque pas d, il y a n-(k-1)d départs possibles.
    count = sum(n - (k - 1) * d for d in range(1, (n - 1) // (k - 1) + 1))
    return Counter({0: comb(n, k) - count, 1: count})


def _ecarts_tries(k, n):
    """Loi exacte du multiensemble des k-1 écarts, rangé par ordre croissant.

    Pour un vecteur d'écarts de span s, chaque permutation distincte donne une
    suite croissante différente, et celle-ci admet n-s positions de départ.
    On énumère les partitions de s en k-1 parts positives, pas les C(n,k)
    sélections. Le nombre de partitions reste modeste pour 16/56 et 20/70.
    """
    out = Counter()
    # Construire les vecteurs triés sans matérialiser les compositions. Les
    # fréquences servent au coefficient multinomial, puis le vecteur lui-même
    # est conservé pour la clé de la loi.
    vector = []

    def partitions(minimum, remaining, slots):
        if slots == 0:
            if remaining == 0:
                counts = Counter(vector)
                permutations = factorial(k - 1)
                for count in counts.values():
                    permutations //= factorial(count)
                out[tuple(vector)] += (n - sum(vector)) * permutations
            return
        maximum = remaining // slots
        for gap in range(minimum, maximum + 1):
            vector.append(gap)
            partitions(gap, remaining - gap, slots - 1)
            vector.pop()

    for span in range(k - 1, n):
        partitions(1, span, k - 1)
    return out


def _paires_proches(k, n, distance=5):
    # À l'ajout de x, seules les valeurs retenues dans [x-distance, x-1]
    # créent de nouvelles paires. Le masque garde exactement cette fenêtre.
    window = (1 << distance) - 1
    states = {(0, 0, 0): 1}  # (taille, masque des derniers numéros, paires)
    for x in range(1, n + 1):
        following = defaultdict(int)
        for (used, mask, pairs), ways in states.items():
            shifted = (mask << 1) & window
            following[(used, shifted, pairs)] += ways
            if used < k:
                following[(used + 1, shifted | 1,
                           pairs + mask.bit_count())] += ways
        states = following
    law = Counter()
    for (used, _mask, pairs), ways in states.items():
        if used == k:
            law[pairs] += ways
    return law


def lois_par_recurrence(k, n):
    """Retourne les lois exactes couvertes, leur total et les champs encore ouverts."""
    if not 2 <= k <= n:
        raise ValueError('régime attendu : 2 <= k <= n')
    total = comb(n, k)
    span = _etendue(k, n)
    consecutive, long_run, runs_ge2 = _suites(k, n)
    decade_counts, max_same, occupied = _dizaines(k, n)
    repeated, terminal_pairs = _finales(k, n)
    laws = {
        'sum': _somme(k, n),
        'span': span,
        'mean_gap': Counter({}),
        'min_gap': _ecart_min(k, n),
        'max_gap': _ecart_max(k, n),
        'longest_consecutive_run': long_run,
        'consecutive_pairs': consecutive,
        'runs_ge2': runs_ge2,
        'decade_counts': decade_counts,
        'max_same_decade': max_same,
        'occupied_decades': occupied,
        'odd_count': _hypergeom(k, n, (n + 1) // 2),
        'low_count': _hypergeom(k, n, (n + 1) // 2),
        'repeated_terminal_digits': repeated,
        'terminal_pair_collisions': terminal_pairs,
        'is_arithmetic_progression': _progression_complete(k, n),
        'sorted_gaps': _ecarts_tries(k, n),
        'clusteredness_close_pairs_5': _paires_proches(k, n),
    }
    # mean_gap = span/(k-1) : mêmes effectifs, autre valeur de classe.
    for s, count in span.items():
        laws['mean_gap'][str(Fraction(s, k - 1))] += count
    converted = {name: {key(value): count for value, count in law.items() if count}
                 for name, law in laws.items()}
    for name, law in converted.items():
        if sum(law.values()) != total:
            raise AssertionError(f'loi {name} de {k}/{n} : {sum(law.values())} != {total}')
    missing = ('arithmetic_triples', 'longest_arithmetic_progression')
    if (k, n) == (16, 56):
        artifact = Path(__file__).with_name('keno-laws-metal-exact-16-56.json')
        source = json.loads(artifact.read_text(encoding='utf-8'))
        expected = {'schema': 'aleaquant-keno-exact-feature-laws-v1',
                    'domain': 56, 'picks': 16, 'total': total}
        if any(source.get(field) != value for field, value in expected.items()):
            raise ValueError(f'artefact Metal Keno 16/56 invalide : {artifact}')
        for field in missing:
            histogram = source.get(field)
            if not isinstance(histogram, dict) or sum(histogram.values()) != total:
                raise ValueError(f'histogramme exact absent/incomplet : {field}')
            converted[field] = {str(int(value)): count for value, count in histogram.items()}
        missing = ()
    return converted, total, missing
