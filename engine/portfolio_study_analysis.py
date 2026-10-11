"""Analyse descriptive d'une étude appariée de géométries, sans sélection MC.

L'écart-type des résumés décrit les constructions entre graines. Il n'est
ni une erreur standard ni un intervalle de confiance de simulation. Les
comptages marginaux ne permettent pas de tester les différences entre deux
portefeuilles évalués sur les mêmes tirages sans leur covariance.
"""
from collections import Counter, defaultdict
from itertools import combinations
import math
from statistics import fmean, pstdev

from portfolio_evaluation import EVENTS, exact_analytics
from portfolio_geometry import portfolio_geometry
from portfolio_import import content_hash, require, values
from portfolio_metrics import metric_values

VERSION = 'aleaquant-paired-portfolio-study-analysis-v1'
CRITERIA = (
    ('portfolio.distinct_pairs@v1', 'max'),
    ('portfolio.distinct_triples@v1', 'max'),
    ('portfolio.number_frequency_sd@v1', 'min'),
    ('portfolio.max_number_overlap@v1', 'min'),
)
INTERPRETIVE_METRICS = CRITERIA + (('portfolio.distinct_star_pairs@v1', 'max'),)
VECTOR_LENGTHS = {
    'portfolio.number_overlap_distribution@v1': 6,
    'portfolio.star_overlap_distribution@v1': 3,
    'portfolio.number_frequencies@v1': 50,
    'portfolio.star_frequencies@v1': 12,
}
MC_KEYS = {
    'portfolio.any_prize_probability@v1': 'any_prize',
    'portfolio.multiple_prizes_probability@v1': 'multiple_prizes',
    'portfolio.at_least_3_numbers_probability@v1': 'at_least_3_numbers',
    'portfolio.at_least_4_numbers_probability@v1': 'at_least_4_numbers',
}


def _finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _stats(series):
    require(bool(series) and all(_finite(x) for x in series), 'série de mesures invalide')
    return {'n': len(series), 'mean': fmean(series), 'min': min(series),
            'max': max(series), 'sd': pstdev(series), 'sd_method': 'population_across_generation_seeds'}


def _measurements(record):
    require(all(key in record for key in ('grids', 'pool_numbers', 'pool_stars', 'content_sha256')),
            'grilles, pools ou empreinte manquants')
    grids = record['grids']
    require(isinstance(grids, list) and 2 <= len(grids) <= 2000, 'taille de portefeuille invalide')
    nums, stars = record['pool_numbers'], record['pool_stars']
    require(isinstance(nums, list) and 5 <= len(nums) <= 50, 'pool de numéros invalide')
    require(isinstance(stars, list) and 2 <= len(stars) <= 12, 'pool d’étoiles invalide')
    values(nums, len(nums), 50, 'pool numéros')
    values(stars, len(stars), 12, 'pool étoiles')
    for grid in grids:
        require(isinstance(grid, list) and len(grid) == 2, 'format de grille invalide')
        values(grid[0], 5, 50, 'numéros')
        values(grid[1], 2, 12, 'étoiles')
        require(set(grid[0]) <= set(nums) and set(grid[1]) <= set(stars), 'grille hors pool')
    require(len({(tuple(sorted(g[0])), tuple(sorted(g[1]))) for g in grids}) == len(grids),
            'grilles répétées')
    require(content_hash(grids) == record['content_sha256'], 'empreinte différente des grilles')
    geometry = portfolio_geometry(grids, 50)
    measured = metric_values(grids, geometry)
    measured['portfolio.jackpot_probability@v1'] = exact_analytics(grids)['jackpot_probability']
    for key, length in VECTOR_LENGTHS.items():
        require(key in measured and isinstance(measured[key], list) and len(measured[key]) == length,
                'métrique vectorielle absente du moteur commun : ' + key)
    number_counts = measured['portfolio.number_frequencies@v1']
    star_counts = measured['portfolio.star_frequencies@v1']
    require(sum(number_counts) == 5 * len(grids) and sum(star_counts) == 2 * len(grids),
            'fréquences incompatibles')
    pairs = len(grids) * (len(grids) - 1) // 2
    require(sum(measured['portfolio.number_overlap_distribution@v1']) == pairs
            and sum(measured['portfolio.star_overlap_distribution@v1']) == pairs,
            'histogramme d’intersections incompatible')
    numbers_in_pool = [number_counts[n - 1] for n in sorted(nums)]
    stars_in_pool = [star_counts[s - 1] for s in sorted(stars)]
    combinations_counts = Counter(tuple(sorted(g[1])) for g in grids)
    return {
        'metrics': measured,
        'pool_frequency_sd': {'numbers': pstdev(numbers_in_pool), 'stars': pstdev(stars_in_pool)},
        'pool_frequencies': {'numbers': {'values': sorted(nums), 'counts': numbers_in_pool},
                             'stars': {'values': sorted(stars), 'counts': stars_in_pool}},
        'star_combinations': {
            'covered': measured['portfolio.distinct_star_pairs@v1'],
            'pool_possible': math.comb(len(stars), 2), 'domain_possible': math.comb(12, 2),
            'counts': [{'stars': list(pair), 'count': combinations_counts.get(pair, 0)}
                       for pair in combinations(sorted(stars), 2)],
        },
        'coverage_denominators': {
            'pairs': {'pool': math.comb(len(nums), 2), 'domain': math.comb(50, 2)},
            'triples': {'pool': math.comb(len(nums), 3), 'domain': math.comb(50, 3)},
            'star_combinations': {'pool': math.comb(len(stars), 2), 'domain': 66},
        },
    }


def _summarize(measurements):
    scalar, vectors = {}, {}
    for key in measurements[0]['metrics']:
        series = [row['metrics'][key] for row in measurements]
        if key in VECTOR_LENGTHS:
            vectors[key] = [_stats([row[i] for row in series]) for i in range(VECTOR_LENGTHS[key])]
        else:
            scalar[key] = _stats(series)
    return {
        'metrics': scalar, 'vectors': vectors,
        'pool_frequency_sd': {part: _stats([r['pool_frequency_sd'][part] for r in measurements])
                              for part in ('numbers', 'stars')},
        'pool_frequencies': {
            part: {'values': measurements[0]['pool_frequencies'][part]['values'],
                   'counts': [_stats([r['pool_frequencies'][part]['counts'][i] for r in measurements])
                              for i in range(len(measurements[0]['pool_frequencies'][part]['values']))]}
            for part in ('numbers', 'stars')},
        'star_combinations': {
            'pool_possible': measurements[0]['star_combinations']['pool_possible'],
            'domain_possible': 66,
            'counts': [{'stars': row['stars'],
                        **_stats([m['star_combinations']['counts'][i]['count'] for m in measurements])}
                       for i, row in enumerate(measurements[0]['star_combinations']['counts'])]},
    }


def _difference(measured, baseline):
    return {
        'metrics': {
            key: ([x - y for x, y in zip(value, baseline['metrics'][key])]
                  if key in VECTOR_LENGTHS else value - baseline['metrics'][key])
            for key, value in measured['metrics'].items()},
        'pool_frequency_sd': {p: measured['pool_frequency_sd'][p] - baseline['pool_frequency_sd'][p]
                              for p in ('numbers', 'stars')},
        'pool_frequencies': {
            p: {'values': measured['pool_frequencies'][p]['values'],
                'counts': [x - y for x, y in zip(measured['pool_frequencies'][p]['counts'],
                                                baseline['pool_frequencies'][p]['counts'])]}
            for p in ('numbers', 'stars')},
        'star_combinations': {
            'pool_possible': measured['star_combinations']['pool_possible'], 'domain_possible': 66,
            'counts': [{'stars': row['stars'], 'count': row['count'] - baseline['star_combinations']['counts'][i]['count']}
                       for i, row in enumerate(measured['star_combinations']['counts'])]},
    }


def _front(records, measured):
    def dominates(a, b):
        if a['content_sha256'] == b['content_sha256']:
            return False
        av, bv = measured[a['id']]['metrics'], measured[b['id']]['metrics']
        signs = [1 if direction == 'max' else -1 for key, direction in CRITERIA]
        differences = [(av[key] - bv[key]) * sign for (key, direction), sign in zip(CRITERIA, signs)]
        return all(x >= 0 for x in differences) and any(x > 0 for x in differences)
    return [b for b in records if not any(dominates(a, b) for a in records)]


def _select(records, measured, weights, maximum):
    require(type(maximum) is int and len(weights) <= maximum <= 12,
            'plafond de finalistes insuffisant pour les quotas ou supérieur à 12')
    front = _front(records, measured)
    front_ids = {r['id'] for r in front}
    def order(row):
        m = measured[row['id']]['metrics']
        return (-m[CRITERIA[0][0]], -m[CRITERIA[1][0]], m[CRITERIA[2][0]],
                m[CRITERIA[3][0]], row['content_sha256'], row['id'])
    selected, reasons, hashes = [], {}, set()
    for weight in weights:
        group = [r for r in records if r['study_factor']['weight'] == weight]
        if any(r['content_sha256'] in hashes for r in group):
            continue  # A selected content also represents its aliases at this factor.
        candidates = [r for r in group if r['id'] in front_ids]
        reason = 'weight_quota_global_front'
        if not candidates:
            candidates, reason = _front(group, measured), 'weight_quota_within_weight_front'
        chosen = min(candidates, key=order)
        selected.append(chosen)
        hashes.add(chosen['content_sha256'])
        reasons[chosen['id']] = reason
    for chosen in sorted(front, key=order):
        if len(selected) >= maximum:
            break
        if chosen['content_sha256'] not in hashes:
            selected.append(chosen)
            hashes.add(chosen['content_sha256'])
            reasons[chosen['id']] = 'global_front_geometry_order'
    return {
        'ids': [r['id'] for r in selected], 'content_sha256': [r['content_sha256'] for r in selected],
        'reasons': reasons, 'global_pareto_ids': [r['id'] for r in sorted(front, key=order)],
        'global_pareto_content_sha256': sorted({r['content_sha256'] for r in front}),
        'global_front_fully_selected': {r['content_sha256'] for r in front} <= hashes,
        'covered_weights': [weight for weight in weights
                            if any(r['study_factor']['weight'] == weight and r['content_sha256'] in hashes for r in records)],
        'maximum': maximum, 'selection_basis': 'exact_geometry_only',
        'criteria': [{'metric_id': key, 'direction': direction} for key, direction in CRITERIA],
        'tie_break': 'pairs desc, triples desc, number SD asc, max number overlap asc, content SHA, record ID',
        'policy': 'One content quota per factor, prefer the global front then its within-factor front; fill with global-front contents in exact geometric order. The complete global front remains reported even when over the limit.',
    }


def _mc_values(simulation, record):
    require(isinstance(simulation, dict), 'simulation manquante')
    n, seed = simulation.get('draws'), simulation.get('seed')
    require(type(n) is int and 1 <= n <= 1_000_000 and type(seed) is int and 0 <= seed < 2 ** 63,
            'protocole MC invalide')
    require(simulation.get('same_draws_for_all') is True and simulation.get('independent_of_generation') is True,
            'protocole MC commun et indépendant requis')
    require(simulation.get('content_sha256') == record['content_sha256'],
            'simulation reliée à un autre contenu')
    require(isinstance(simulation.get('metrics'), dict) and set(simulation['metrics']) == set(EVENTS),
            'événements MC inconnus ou manquants')
    for name in EVENTS:
        event = simulation['metrics'][name]
        require(isinstance(event, dict), 'format d’événement MC invalide')
        count, probability = event.get('count'), event.get('probability')
        require(type(count) is int and 0 <= count <= n and _finite(probability)
                and 0 <= probability <= 1
                and math.isclose(probability, count / n, rel_tol=1e-12, abs_tol=1e-12),
                'compte ou probabilité MC incompatible')
    raw = {key: simulation['metrics'][event]['probability'] for key, event in MC_KEYS.items()}
    mean = simulation.get('mean_winning_grids')
    require(_finite(mean), 'moyenne MC invalide')
    any_p, multiple_p = (simulation['metrics'][event]['probability']
                         for event in ('any_prize', 'multiple_prizes'))
    require(multiple_p <= any_p and any_p + multiple_p - 1e-12 <= mean
            <= any_p + (len(record['grids']) - 1) * multiple_p + 1e-12,
            'moyenne ou événements MC incohérents')
    require(simulation['metrics']['at_least_4_numbers']['count']
            <= simulation['metrics']['at_least_3_numbers']['count']
            <= simulation['metrics']['any_prize']['count'], 'seuils MC incohérents')
    raw['portfolio.mean_winning_grids@v1'] = mean
    return raw


def _common_metadata(simulations):
    """Les identités fournies par l'évaluateur doivent toutes être communes."""
    result = {}
    for key in ('protocol_sha256', 'draw_stream_sha256', 'source_sha256'):
        present = [key in s for s in simulations]
        if any(present):
            require(all(present), 'provenance MC partielle : ' + key)
            identities = {s[key] for s in simulations if isinstance(s[key], str)}
            require(len(identities) == 1 and all(isinstance(s[key], str) for s in simulations),
                    'identités MC différentes : ' + key)
            identity = next(iter(identities))
            require(len(identity) == 64 and all(c in '0123456789abcdef' for c in identity),
                    'empreinte MC invalide : ' + key)
            result[key] = identity
    return result


def _simulation_analysis(records, weights, seeds, baseline, forbidden):
    availability = ['simulation' in r for r in records]
    if not any(availability):
        return {'status': 'not_evaluated', 'inference': 'none'}
    require(all(availability), 'MC partiel : les facteurs ne sont pas tous évalués')
    raw = {r['id']: _mc_values(r['simulation'], r) for r in records}
    protocols = {(r['simulation']['seed'], r['simulation']['draws']) for r in records}
    require(len(protocols) == 1, 'protocoles MC différents entre facteurs')
    metadata = _common_metadata([r['simulation'] for r in records])
    seed, draws = next(iter(protocols))
    require(seed not in forbidden, 'graine MC réutilisée pour construction ou pool')
    by_content = {}
    for record in records:
        previous = by_content.setdefault(record['content_sha256'], raw[record['id']])
        require(previous == raw[record['id']], 'mêmes grilles et mêmes tirages avec résultats MC différents')
    indexed = {(r['study_factor']['weight'], r['study_factor']['seed']): r for r in records}
    by_factor, paired = [], []
    for weight in weights:
        rows = [raw[indexed[weight, s]['id']] for s in seeds]
        by_factor.append({'weight': weight, 'repetitions': len(seeds),
                          'metrics': {key: _stats([row[key] for row in rows]) for key in rows[0]}})
        differences = [{key: row[key] - raw[indexed[baseline, s]['id']][key] for key in row}
                       for s, row in zip(seeds, rows)]
        paired.append({'weight_a': baseline, 'weight_b': weight, 'repetitions': len(seeds),
                       'metrics': {key: _stats([row[key] for row in differences]) for key in differences[0]},
                       'by_seed': [{'seed': s, 'differences': row} for s, row in zip(seeds, differences)]})
    return {'status': 'complete', 'seed': seed, 'draws': draws, **metadata, 'by_factor': by_factor,
            'paired_differences': paired, 'inference': 'descriptive_only_no_paired_draw_covariance',
            'warning': 'Differences are arithmetic descriptions. Marginal Wilson intervals do not supply a confidence interval or significance test for differences on common draws. SD describes variability between generation seeds.'}


def _effect(series, direction):
    sign = 1 if direction == 'max' else -1
    favorable = sum(x * sign > 1e-12 for x in series)
    unfavorable = sum(x * sign < -1e-12 for x in series)
    stable = len(series) - favorable - unfavorable
    label = ('stable' if stable == len(series) else 'mixed' if favorable and unfavorable
             else 'improved' if favorable else 'degraded')
    return {'classification': label, 'favorable_seeds': favorable, 'unfavorable_seeds': unfavorable,
            'unchanged_seeds': stable, 'mean_difference': fmean(series)}


def analyze_study(records, max_finalists=12, baseline_weight=0.0, confirmation=None):
    """Agréger un plan rectangulaire poids × graines, puis retenir la géométrie.

    confirmation est le mapping content_sha256 -> simulation d'un nouvel
    evaluate_many(...)["results"], pour les seuls contenus finalistes.
    """
    require(isinstance(records, list) and len(records) >= 4, 'étude appariée trop petite')
    require(_finite(baseline_weight), 'poids témoin invalide')
    ids, indexed, measured, forbidden = set(), {}, {}, set()
    controls, objective_controls, method_controls = None, None, None
    profile_availability = ['constraint_profile' in r for r in records if isinstance(r, dict)]
    require(not any(profile_availability) or all(profile_availability), 'profils de contraintes partiellement renseignés')
    for record in records:
        require(isinstance(record, dict) and isinstance(record.get('id'), str) and bool(record['id']), 'fiche invalide')
        require(record['id'] not in ids, 'identifiant de fiche répété')
        ids.add(record['id'])
        factor = record.get('study_factor')
        require(isinstance(factor, dict) and set(factor) == {'weight', 'seed'}, 'facteur poids/graine invalide')
        weight, seed = factor['weight'], factor['seed']
        require(_finite(weight) and 0 <= weight <= 1_000_000 and type(seed) is int and 0 <= seed <= 2 ** 32 - 1,
                'poids ou graine invalide')
        require((weight, seed) not in indexed, 'cellule poids/graine répétée')
        indexed[weight, seed] = record
        measured[record['id']] = _measurements(record)
        current = (tuple(sorted(record['pool_numbers'])), tuple(sorted(record['pool_stars'])), len(record['grids']))
        if controls is None:
            controls = current
        require(current == controls, 'pools ou nombre de grilles différents entre facteurs')
        generation = record.get('generation', {})
        require(isinstance(generation, dict), 'provenance de génération invalide')
        require(generation.get('seed', seed) == seed, 'graine réelle différente du facteur apparié')
        forbidden.add(seed)
        if 'pool_seed' in generation:
            forbidden.add(generation['pool_seed'])
        profile = record.get('constraint_profile')
        if profile is not None:
            require(isinstance(profile, dict) and isinstance(profile.get('objectives'), dict)
                    and isinstance(profile['objectives'].get('minimize_overlap'), dict)
                    and 'numbers' in profile['objectives']['minimize_overlap'],
                    'objectifs de contraintes invalides')
            require(profile['objectives']['minimize_overlap']['numbers'] == weight,
                    'poids réel différent du facteur déclaré')
            fixed = {k: v for k, v in profile['objectives'].items() if k != 'minimize_overlap'}
            fixed['minimize_overlap'] = {k: v for k, v in profile['objectives']['minimize_overlap'].items() if k != 'numbers'}
            if objective_controls is None:
                objective_controls = fixed
            require(fixed == objective_controls, 'autres objectifs différents entre facteurs')
        if 'method' in generation:
            method = (generation['method'], generation.get('candidates_per_step'))
            if method_controls is None:
                method_controls = method
            require(method == method_controls, 'méthode ou nombre de propositions différents entre facteurs')
    weights = sorted({w for w, s in indexed})
    seeds = sorted({s for w, s in indexed})
    require(len(weights) >= 2 and len(seeds) >= 2 and baseline_weight in weights, 'au moins deux poids et deux graines, dont le témoin, sont requis')
    require(set(indexed) == {(w, s) for w in weights for s in seeds}, 'graines appariées manquantes entre facteurs')
    ordered = [indexed[w, s] for w in weights for s in seeds]
    selection = _select(ordered, measured, weights, max_finalists)
    by_factor, paired, effects = [], [], []
    for weight in weights:
        rows = [measured[indexed[weight, s]['id']] for s in seeds]
        by_factor.append({'weight': weight, 'repetitions': len(seeds), 'seeds': seeds,
                          **_summarize(rows)})
        differences = [_difference(row, measured[indexed[baseline_weight, s]['id']])
                       for s, row in zip(seeds, rows)]
        paired.append({'weight_a': baseline_weight, 'weight_b': weight, 'repetitions': len(seeds),
                       **_summarize(differences),
                       'by_seed': [{'seed': s, 'id_a': indexed[baseline_weight, s]['id'],
                                    'id_b': indexed[weight, s]['id'], **delta}
                                   for s, delta in zip(seeds, differences)]})
        if weight != baseline_weight:
            effects.append({'weight_a': baseline_weight, 'weight_b': weight,
                            'metrics': {key: _effect([row['metrics'][key] for row in differences], direction)
                                        for key, direction in INTERPRETIVE_METRICS}})
    mc = _simulation_analysis(ordered, weights, seeds, baseline_weight, forbidden)
    confirmation_output = {'status': 'not_evaluated'}
    if confirmation is not None:
        require(isinstance(confirmation, dict) and set(confirmation) == set(selection['content_sha256']),
                'confirmation : contenus finalistes manquants ou supplémentaires')
        selected = [next(r for r in ordered if r['id'] == identifier) for identifier in selection['ids']]
        confirmed = {r['id']: _mc_values(confirmation[r['content_sha256']], r) for r in selected}
        metadata = _common_metadata(list(confirmation.values()))
        protocols = {(s['seed'], s['draws']) for s in confirmation.values()}
        require(len(protocols) == 1, 'confirmation : protocoles différents')
        seed, draws = next(iter(protocols))
        require(seed not in forbidden and (mc['status'] != 'complete' or seed != mc['seed']),
                'confirmation : graine réutilisée pour comparaison/construction/pool')
        confirmation_output = {'status': 'complete', 'seed': seed, 'draws': draws, **metadata,
                               'by_record_id': confirmed, 'inference': 'descriptive_only',
                               'scope': 'Selected geometric finalists only; no extrapolation to all generation seeds.'}
    labels = {CRITERIA[0][0]: 'couverture des paires', CRITERIA[1][0]: 'couverture des triplets',
              CRITERIA[2][0]: 'dispersion des occurrences de numéros', CRITERIA[3][0]: 'intersection maximale',
              'portfolio.distinct_star_pairs@v1': 'couverture des paires d’étoiles'}
    french = {'stable': 'stable', 'mixed': 'effet variable', 'improved': 'améliorée', 'degraded': 'dégradée'}
    synthesis = [f'{len(seeds)} graines appariées par poids ; les résultats portent sur toutes les constructions de ce plan.']
    for item in effects:
        descriptions = [f"{labels[key]} : {french[value['classification']]} ({value['favorable_seeds']} favorables, {value['unfavorable_seeds']} défavorables, {value['unchanged_seeds']} inchangées ; différence moyenne {value['mean_difference']:+.4g})"
                        for key, value in item['metrics'].items()]
        synthesis.append(f"Poids {item['weight_b']:g} comparé au poids {baseline_weight:g} : " + ' ; '.join(descriptions) + '.')
    synthesis.append('À nombre de grilles distinctes égal, l’espérance théorique des grilles gagnantes et la probabilité exacte du jackpot restent identiques. Le MC décrit les constructions ; aucune différence statistiquement significative n’est établie sans covariance des événements sur les tirages communs.')
    return {'version': VERSION, 'baseline_weight': baseline_weight, 'weights': weights,
            'seeds': seeds, 'repetitions': len(seeds), 'record_count': len(ordered),
            'controls': {'pool_numbers': list(controls[0]), 'pool_stars': list(controls[1]), 'grid_count': controls[2],
                         'other_objectives': objective_controls,
                         'method_and_candidates_per_step': list(method_controls) if method_controls is not None else None},
            'geometry_by_record': measured, 'by_factor': by_factor, 'paired_differences': paired,
            'paired_effects': effects, 'finalist_ids': selection['ids'], 'finalist_selection': selection,
            'monte_carlo_descriptive': mc, 'confirmation': confirmation_output, 'synthesis': synthesis,
            'definitions': {
                'sd': 'Population SD across paired generation seeds, never an MC standard error.',
                'number_frequencies': '50 occurrence counts in number order 1..50, including zeros outside the pool.',
                'star_frequencies': '12 occurrence counts in star order 1..12, including zeros outside the pool.',
                'pool_frequencies': 'The same occurrence counts restricted to the fixed declared pool, including unused values.',
                'star_combinations': 'Unordered two-star combinations; counts include zero for each pair of the pool; full domain denominator C(12,2)=66.',
                'paired_differences': 'Weight B minus baseline A using the same generation seed; exact geometry deltas. MC deltas are only arithmetic descriptions.',
            }}
