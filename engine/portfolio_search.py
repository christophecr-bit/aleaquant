"""Bounded portfolio search driven only by exact grid geometry.

All random streams have explicit seeds. Constraints apply before each grid is
accepted; simulations and observed lottery gains never select a candidate.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations, product
import math
import random
import time

from portfolio_contract import resolve_pool, validate_grids, validate_profile
from portfolio_import import content_hash


METHODS = frozenset(('random', 'greedy', 'enumerate', 'prototype_greedy'))
FAMILIES = frozenset(('RANDOM', 'BALANCED', 'LOW_OVERLAP', 'COVERAGE', 'CONCENTRATED'))


class _Scorer:
    """Exact incremental coverage, dispersion, and squared intersections."""

    def __init__(self, profile, numbers, stars):
        self.weights = profile['objectives']
        self.number_domain_size = len(numbers)
        self.star_domain_size = len(stars)
        self.number_size = profile['game']['numbers_per_grid']
        self.star_size = profile['game']['stars_per_grid']
        self.number_sets, self.star_sets = [], []
        self.number_counts, self.star_counts = Counter(), Counter()
        self.pairs, self.triples = set(), set()
        self.score = 0.0

    @staticmethod
    def _dispersion_delta(counts, selected, size, total, domain_size):
        # sum((frequency - mean)^2) = sum(frequency^2) - picks^2 / pool_size.
        squares = sum(2 * counts[value] + 1 for value in selected)
        mean_correction = size * size * (2 * total + 1) / domain_size
        return squares - mean_correction

    def addition(self, grid):
        main, stars = frozenset(grid[0]), frozenset(grid[1])
        pairs = set(combinations(sorted(main), 2))
        triples = set(combinations(sorted(main), 3))
        main_overlap = sum(len(main & previous) ** 2 for previous in self.number_sets)
        star_overlap = sum(len(stars & previous) ** 2 for previous in self.star_sets)
        main_balance = self._dispersion_delta(
            self.number_counts, main, self.number_size, len(self.number_sets), self.number_domain_size)
        star_balance = self._dispersion_delta(
            self.star_counts, stars, self.star_size, len(self.star_sets), self.star_domain_size)
        w = self.weights
        overlap = w['minimize_overlap']
        score = (w['distinct_pairs'] * len(pairs - self.pairs)
                 + w['distinct_triples'] * len(triples - self.triples)
                 - w['balance_numbers'] * main_balance
                 - w['balance_stars'] * star_balance
                 + w['concentration'] * main_overlap
                 - overlap['numbers'] * main_overlap
                 - overlap['stars'] * star_overlap)
        return float(score)

    def add(self, grid):
        self.score += self.addition(grid)
        main, stars = frozenset(grid[0]), frozenset(grid[1])
        self.number_sets.append(main)
        self.star_sets.append(stars)
        self.number_counts.update(main)
        self.star_counts.update(stars)
        self.pairs.update(combinations(sorted(main), 2))
        self.triples.update(combinations(sorted(main), 3))


class _PrototypeScorer(_Scorer):
    """Literal prototype step score; frequency costs use current occurrences."""

    def addition(self, grid):
        main, stars = frozenset(grid[0]), frozenset(grid[1])
        pairs = set(combinations(sorted(main), 2))
        triples = set(combinations(sorted(main), 3))
        overlap = [len(main & previous) for previous in self.number_sets]
        w = self.weights
        # Keep the prototype's expression order to preserve score ties exactly.
        return float(w['distinct_triples'] * len(triples - self.triples)
                     + w['distinct_pairs'] * len(pairs - self.pairs)
                     - sum(self.number_counts[value] for value in main) * w['balance_numbers']
                     - sum(self.star_counts[value] for value in stars) * w['balance_stars']
                     - sum(value * value for value in overlap) * w['minimize_overlap']['numbers'])


def _scorer_for(profile, numbers, stars):
    scorer = _PrototypeScorer if profile['search']['method'] == 'prototype_greedy' else _Scorer
    return scorer(profile, numbers, stars)


def portfolio_score(grids, profile):
    """Weighted descriptive score; balances include unused pool values.

Concentration rewards squared number intersections. The two overlap penalties
apply separately to numbers and stars. The explicit prototype_greedy mode sums
its frequency-based incremental scores instead of the variance objective.
No probability estimate enters either score.
"""
    numbers, stars = resolve_pool(profile)
    scorer = _scorer_for(profile, numbers, stars)
    for grid in grids:
        scorer.add(grid)
    return scorer.score


def _key(grid):
    return tuple(grid[0]), tuple(grid[1])


def _fits(grid, grids, keys, limits):
    if _key(grid) in keys:
        return False
    main, stars = set(grid[0]), set(grid[1])
    return all(len(main & set(previous[0])) <= limits['numbers']
               and len(stars & set(previous[1])) <= limits['stars']
               for previous in grids)


def generate_candidates(profile, progress=None):
    """Return unique candidates, or an explicit bounded-search exhaustion.

``attempts`` counts proposed grids, including rejected samples. Each candidate
trial advances from ``search.seed``, skipping pool/evaluation seeds, and records
its actual seed. Rejections are
counts by cause. Progress receives plain dictionaries after accepted grids and
candidates; it does not participate in candidate selection.
    """
    validate_profile(profile)
    search = profile['search']
    method = search['method']
    if method not in METHODS:
        raise ValueError('méthode de recherche inconnue')
    if profile['family'] not in FAMILIES:
        raise ValueError('famille de portefeuille inconnue')
    if progress is not None and not callable(progress):
        raise ValueError('progress doit être une fonction')
    numbers, stars = resolve_pool(profile)
    numbers, stars = sorted(numbers), sorted(stars)
    main_size = profile['game']['numbers_per_grid']
    star_size = profile['game']['stars_per_grid']
    grid_count = profile['constraints']['grid_count']
    capacity = math.comb(len(numbers), main_size) * math.comb(len(stars), star_size)
    if method == 'enumerate' and capacity != grid_count:
        raise ValueError('enumerate exige de couvrir exactement tout le pool')
    limits = profile['constraints']['max_pairwise_overlap']
    requested = search['candidate_count']
    started = time.monotonic()
    attempts = 0
    rejections = {'hard_constraints': 0, 'duplicate_proposal': 0, 'duplicate_portfolio': 0}
    candidates, hashes = [], set()
    reason = None
    trial_index = 0
    reserved_seeds = {profile['pool']['seed'], profile['evaluation']['seed']}

    def bound_reason():
        if attempts >= search['max_attempts']:
            return 'max_attempts'
        if time.monotonic() - started >= search['max_seconds']:
            return 'max_seconds'
        return None

    def report(phase, accepted=0):
        if progress:
            progress({'phase': phase, 'attempts': attempts, 'rejections': dict(rejections),
                      'candidates': len(candidates), 'candidate_index': len(candidates),
                      'accepted_grids': accepted, 'elapsed_seconds': time.monotonic() - started})

    def prefix_valid(grids):
        # The shared validator checks an exact size. Keep all other constraints.
        partial_profile = dict(profile)
        partial_profile['constraints'] = dict(profile['constraints'], grid_count=len(grids))
        return not validate_grids(grids, partial_profile)

    # When all available grids are required, there is exactly one unordered
    # portfolio. This known finite bound also prevents repeated duplicate trials.
    finite_count = 1 if capacity == grid_count else None
    if finite_count is None and capacity <= 1000:
        finite_count = math.comb(capacity, grid_count)

    while len(candidates) < requested:
        reason = bound_reason()
        if reason:
            break
        if finite_count is not None and len(hashes) >= finite_count:
            reason = 'finite_space_exhausted'
            break
        seed = search['seed'] + trial_index
        while seed in reserved_seeds:
            trial_index += 1
            seed = search['seed'] + trial_index
        if seed > 2**32 - 1:
            reason = 'seed_space_exhausted'
            break
        trial_index += 1
        rng = random.Random(seed)
        grids, keys = [], set()
        scorer = _scorer_for(profile, numbers, stars)
        if method == 'enumerate':
            proposals = product(combinations(numbers, main_size), combinations(stars, star_size))
            for main, second in proposals:
                reason = bound_reason()
                if reason:
                    break
                attempts += 1
                grid = [list(main), list(second)]
                if not _fits(grid, grids, keys, limits) or not prefix_valid(grids + [grid]):
                    rejections['hard_constraints'] += 1
                    reason = 'constraints_exhausted'
                    break
                grids.append(grid)
                keys.add(_key(grid))
                scorer.add(grid)
                report('building', len(grids))
        else:
            for _ in range(grid_count):
                best, best_score = None, None
                seen_at_step = set()
                proposals_at_step = 0
                # RANDOM uses rejection sampling until the next legal grid is
                # accepted. A duplicate does not discard the accepted prefix.
                # With only uniqueness caps this is uniform over remaining grids.
                # The per-step candidate window belongs to greedy selection;
                # both methods still obey the global attempt and time bounds.
                while method == 'random' or proposals_at_step < search['candidates_per_step']:
                    reason = bound_reason()
                    if reason:
                        break
                    attempts += 1
                    proposals_at_step += 1
                    grid = [sorted(rng.sample(numbers, main_size)), sorted(rng.sample(stars, star_size))]
                    key = _key(grid)
                    if key in keys or (method in ('greedy', 'prototype_greedy') and key in seen_at_step):
                        rejections['duplicate_proposal'] += 1
                        continue
                    if method in ('greedy', 'prototype_greedy'):
                        seen_at_step.add(key)
                    if not _fits(grid, grids, keys, limits):
                        rejections['hard_constraints'] += 1
                        continue
                    score = scorer.addition(grid)
                    if best is None or score > best_score:
                        best, best_score = grid, score
                    if method == 'random':
                        break
                # A truncated window would choose among fewer proposals than
                # the archived prototype. Do not publish that altered result.
                if method == 'prototype_greedy' and reason:
                    break
                if best is None:
                    if method == 'prototype_greedy':
                        reason = 'candidate_window_exhausted'
                    break
                if not prefix_valid(grids + [best]):
                    rejections['hard_constraints'] += 1
                    break
                grids.append(best)
                keys.add(_key(best))
                scorer.add(best)
                report('building', len(grids))
                if reason and len(grids) < grid_count:
                    break
        if len(grids) == grid_count:
            errors = validate_grids(grids, profile)
            if errors:
                rejections['hard_constraints'] += 1
            else:
                digest = content_hash(grids)
                if digest in hashes:
                    rejections['duplicate_portfolio'] += 1
                else:
                    hashes.add(digest)
                    candidates.append({'grids': grids, 'seed': seed, 'method': method,
                                       'candidate_index': len(candidates), 'score': scorer.score})
                    report('candidate', len(grids))
        if method in ('enumerate', 'prototype_greedy'):
            if len(candidates) < requested and not reason and method == 'enumerate':
                reason = 'finite_space_exhausted'
            break
        if reason:
            break
    complete = len(candidates) == requested
    return {'status': 'complete' if complete else 'search_exhausted', 'candidates': candidates,
            'attempts': attempts, 'rejections': rejections,
            'stopped_reason': None if complete else (reason or 'finite_space_exhausted')}
