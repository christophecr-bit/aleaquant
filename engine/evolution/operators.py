"""Deterministic, single-attempt operators and exact geometric selection.

``construct_candidate(operator, parents, profile, rng, attempt_index)`` takes
one parent record for a mutation or two for crossover. Each record provides
``id`` and ``grids``; a supplied ``content_sha256`` must match its grids.
The caller owns the explicit ``random.Random`` stream and attempt budget.
An impossible, unchanged or invalid proposal returns ``None`` without retry
or repair. Invalid inputs raise ``ValueError``. A successful payload contains
``grids``, ``operator``, graph ``parent_ids`` (``portfolio:<sha>``), and metadata
with attempt and parent context IDs. Conditional guarantees are deliberately
left to the shared pipeline: every child must be validated and proved there.

``select_survivors(candidates, profile, population_size)`` returns original
records, without modifying them. It recalculates the four exact criteria from
grids, deduplicates portfolio contents, then fills successive Pareto layers.
Within a layer the order is pairs descending, triples descending, number
frequency SD ascending, maximum number overlap ascending, SHA and record ID.
There is no Monte-Carlo, cached-score or weighted-objective selection.
"""
from __future__ import annotations

from copy import deepcopy
import random

from portfolio_contract import resolve_pool, validate_grids
from portfolio_geometry import portfolio_geometry
from portfolio_import import content_hash, require

OPERATORS = ('replace_number_v1', 'swap_numbers_v1', 'replace_grid_v1', 'grid_crossover_v1')
SELECTION_CRITERIA = (
    ('portfolio.distinct_pairs@v1', 'max'),
    ('portfolio.distinct_triples@v1', 'max'),
    ('portfolio.number_frequency_sd@v1', 'min'),
    ('portfolio.max_number_overlap@v1', 'min'),
)


def _record_hash(record, profile):
    require(isinstance(record, dict) and isinstance(record.get('id'), str)
            and bool(record['id']), 'parent/candidate record requires a nonempty id')
    errors = validate_grids(record.get('grids'), profile)
    require(not errors, 'invalid parent/candidate grids: ' + '; '.join(errors))
    checksum = content_hash(record['grids'])
    require('content_sha256' not in record or record['content_sha256'] == checksum,
            'parent/candidate content hash differs from grids')
    return checksum


def _grid_key(grid):
    return tuple(grid[0]), tuple(grid[1])


def construct_candidate(operator, parents, profile, rng, attempt_index):
    """Propose one full child, or reject it; never spend hidden retry attempts."""
    require(operator in OPERATORS, 'unknown evolution operator')
    require(isinstance(rng, random.Random), 'operator requires an explicit random.Random stream')
    require(type(attempt_index) is int and attempt_index >= 0, 'attempt_index requires a nonnegative integer')
    count = 2 if operator == 'grid_crossover_v1' else 1
    require(isinstance(parents, list) and len(parents) == count, 'operator parent count differs')
    hashes = [_record_hash(parent, profile) for parent in parents]
    require(len({parent['id'] for parent in parents}) == len(parents), 'parent context ids are repeated')
    numbers, stars = resolve_pool(profile)
    grids = deepcopy(parents[0]['grids'])
    m = len(grids)
    metadata = {'attempt_index': attempt_index,
                'parent_context_ids': [parent['id'] for parent in parents],
                'requires_pipeline_validation': True}
    if operator == 'replace_number_v1':
        index = rng.randrange(m)
        choices = sorted(set(numbers) - set(grids[index][0]))
        if not choices:
            return None
        removed, added = rng.choice(grids[index][0]), rng.choice(choices)
        grids[index][0] = sorted((set(grids[index][0]) - {removed}) | {added})
        metadata.update(grid_index=index, removed_number=removed, added_number=added)
    elif operator == 'swap_numbers_v1':
        if m < 2:
            return None
        first, second = rng.sample(range(m), 2)
        left, right = set(grids[first][0]), set(grids[second][0])
        left_only, right_only = sorted(left - right), sorted(right - left)
        if not left_only or not right_only:
            return None
        a, b = rng.choice(left_only), rng.choice(right_only)
        grids[first][0] = sorted((left - {a}) | {b})
        grids[second][0] = sorted((right - {b}) | {a})
        metadata.update(grid_indices=[first, second], swapped_numbers=[a, b])
    elif operator == 'replace_grid_v1':
        index = rng.randrange(m)
        grids[index] = [sorted(rng.sample(numbers, 5)), sorted(rng.sample(stars, 2))]
        metadata.update(grid_index=index)
    else:
        if m < 2 or hashes[0] == hashes[1]:
            return None
        first = {_grid_key(grid) for grid in parents[0]['grids']}
        second = {_grid_key(grid) for grid in parents[1]['grids']}
        # Exclusive anchors prove that both parents contribute and that the
        # result differs from either parent, even when most grids are shared.
        left_only, right_only = sorted(first - second), sorted(second - first)
        if not left_only or not right_only:
            return None
        anchors = [rng.choice(left_only), rng.choice(right_only)]
        remaining = sorted((first | second) - set(anchors))
        chosen = sorted(anchors + rng.sample(remaining, m - 2))
        grids = [[list(numbers_part), list(stars_part)] for numbers_part, stars_part in chosen]
        metadata['grid_parent_context_ids'] = [
            [parent['id'] for parent, keys in zip(parents, (first, second)) if key in keys]
            for key in chosen]
    if validate_grids(grids, profile) or content_hash(grids) in hashes:
        return None
    return {'grids': grids, 'operator': operator,
            'parent_ids': ['portfolio:' + checksum for checksum in hashes], 'metadata': metadata}


def _selection_values(record):
    geometry = portfolio_geometry(record['grids'], 50)
    # All comparable records have the same m. For m=1 the undefined maximum
    # is a constant tie criterion; zero here affects only deterministic ranking.
    maximum = geometry['overlap_max'] if geometry['overlap_max'] is not None else 0
    return (geometry['coverage'][2]['covered'], geometry['coverage'][3]['covered'],
            geometry['occurrence_sd'], maximum)


def _dominates(left, right):
    comparisons = (left[0] >= right[0], left[1] >= right[1],
                   left[2] <= right[2], left[3] <= right[3])
    return all(comparisons) and left != right


def select_survivors(candidates, profile, population_size):
    """Fill Pareto layers with distinct contents; return fewer if insufficient."""
    require(isinstance(candidates, list), 'candidate records require a list')
    require(type(population_size) is int and population_size > 0, 'population_size requires a positive integer')
    unique, contexts = {}, {}
    for record in candidates:
        checksum = _record_hash(record, profile)
        require(record['id'] not in contexts or contexts[record['id']] == checksum,
                'candidate context id denotes different portfolio contents')
        contexts[record['id']] = checksum
        if checksum not in unique or record['id'] < unique[checksum]['id']:
            unique[checksum] = record
    remaining = [(record, checksum, _selection_values(record)) for checksum, record in unique.items()]
    selected = []
    while remaining and len(selected) < population_size:
        front = [row for row in remaining
                 if not any(_dominates(other[2], row[2]) for other in remaining)]
        front.sort(key=lambda row: (-row[2][0], -row[2][1], row[2][2], row[2][3], row[1], row[0]['id']))
        selected.extend(row[0] for row in front[:population_size - len(selected)])
        front_hashes = {row[1] for row in front}
        remaining = [row for row in remaining if row[1] not in front_hashes]
    return selected
