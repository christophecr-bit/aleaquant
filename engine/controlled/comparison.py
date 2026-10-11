"""Qualify RANDOM controls and describe comparisons without MC selection.

Qualification is recomputed from profiles, grids and shared-engine provenance;
an incoming ``qualified`` label has no authority. Call ``qualify_controls``
before evaluation with ``require_evaluation=False``, and again before publishing
with the declared protocol and generation signature. ``benchmark`` requires
complete common comparison and independent confirmation roles. It only reads
records: it never generates portfolios, draws MC samples or selects parents.
"""
from collections import defaultdict
import math
from statistics import fmean, pstdev

from portfolio_contract import resolve_pool, validate_grids, validate_profile
import portfolio_evaluation as mc
from portfolio_geometry import portfolio_geometry
from portfolio_import import content_hash, digest, require
from portfolio_metrics import metric_values
from portfolio_pipeline import check_record

VERSION = 'aleaquant-controlled-comparison-v1'
ROLES = ('same_pool', 'full_domain')
CONTROL_COUNT = 10


def _finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _protocol(profile):
    return mc._protocol({k: v for k, v in profile['evaluation'].items() if k != 'max_certificate_cases'})


def _physical(record):
    require(isinstance(record, dict) and isinstance(record.get('id'), str) and record['id'], 'record id absent')
    profile = record['constraint_profile']
    validate_profile(profile)
    check_record(record)
    require(not validate_grids(record['grids'], profile), 'invalid grids')
    require(record['family'] == profile['family'], 'family differs from constraint_profile')
    require(record['rule_id'] == profile['game']['rule_id'] and record['game_id'] == profile['game']['id'], 'rule/game differs from profile')
    require(record['format_id'] == '5of50+2of12', 'grid format differs from rules')
    require(type(record['profile_version']) is int and record['profile_version'] == profile['version'], 'profile version differs')
    require(profile['pool']['method'] == 'explicit', 'explicit pool required')
    numbers, stars = resolve_pool(profile)
    require(record['pool_numbers'] == numbers and record['pool_stars'] == stars, 'record pool differs from profile')
    m = len(record['grids'])
    require(type(record['grid_count']) is int and record['grid_count'] == m, 'grid count differs')
    cost = m * profile['game']['unit_price_eur']
    require(_finite(record['budget_actual_eur']) and record['budget_actual_eur'] == cost
            and record['budget_eur'] == cost and record['unit_price_eur'] == profile['game']['unit_price_eur'], 'actual cost differs from grids/rules')
    require(record['budget_max_eur'] == profile['constraints']['budget_max_eur'], 'maximum budget differs from profile')
    require(type(record['generation']['seed']) is int and 0 <= record['generation']['seed'] <= 2 ** 32 - 1,
            'generation seed must be a bounded integer')
    require(type(record['generation']['pool_seed']) is int
            and record['generation']['pool_seed'] == profile['pool']['seed'], 'generation pool seed differs')
    return {'game': profile['game'], 'schema_version': profile['schema_version'],
            'grid_count': m, 'cost_eur': cost, 'constraints': profile['constraints'],
            'pool_numbers': numbers, 'pool_stars': stars}


def _factor(record):
    factor = record['study_factor']
    require(isinstance(factor, dict) and _finite(factor['weight']), 'ablation weight absent/invalid')
    require(type(factor['seed']) is int and factor['seed'] == record['generation']['seed'], 'ablation seed differs from generation')
    require(factor['weight'] == record['constraint_profile']['objectives']['minimize_overlap']['numbers'], 'weight differs from executed profile')
    return factor['weight'], factor['seed']


def _control(record, physical, expected_protocol):
    profile, generation = record['constraint_profile'], record['generation']
    metadata = record['reference_benchmark']
    require(metadata['role'] in ROLES, 'undeclared control pool role')
    require(metadata.get('selection_eligible') is False, 'control must be excluded from selection')
    require(all(record.get(key) is not True for key in ('is_starting_parent', 'is_survivor', 'is_finalist')),
            'control cannot be a parent, survivor or selection finalist')
    require(not record['lineage']['parent_ids'], 'RANDOM control cannot have parents')
    require(record['family'] == profile['family'] == 'RANDOM'
            and profile['search']['method'] == generation['method'] == 'random',
            'control must execute RANDOM/random, including its constraint profile')
    require(record.get('display_family', 'RANDOM') == 'RANDOM', 'control display family differs')
    require(record['profile_object'] == profile and record['config_sha256'] == digest(profile),
            'control frozen profile/config hash differs')
    require(generation['parameters'] == profile['search'] and profile['search']['candidate_count'] == 1
            and generation['candidate_index'] == 0, 'control must be one untargeted candidate under its declared search')
    objectives = profile['objectives']
    require(all(objectives[key] == 0 for key in objectives if key != 'minimize_overlap')
            and objectives['minimize_overlap']['numbers'] == objectives['minimize_overlap']['stars'] == 0,
            'RANDOM control objectives must be zero')
    require(type(metadata['generation_seed']) is int
            and metadata['generation_seed'] == generation['seed'] == profile['search']['seed'], 'control generation seed differs')
    for key in ('game', 'schema_version', 'grid_count', 'cost_eur', 'constraints'):
        require(physical[key] == expected_protocol['physical'][key], 'control ' + key + ' differs from MAIN')
    if metadata['role'] == 'same_pool':
        require(physical['pool_numbers'] == expected_protocol['physical']['pool_numbers']
                and physical['pool_stars'] == expected_protocol['physical']['pool_stars'], 'same_pool control uses another pool')
    else:
        require(physical['pool_numbers'] == list(range(1, 51))
                and physical['pool_stars'] == list(range(1, 13)), 'full_domain control must use explicit 50/12 domain')
    require(_protocol(profile) == expected_protocol['protocol'], 'control declared evaluation protocol differs')


def _role_payload(record, role):
    return (record['evaluation'], record['simulation']) if role == 'comparison' else (
        record['confirmation']['evaluation'], record['confirmation']['simulation'])


def _mc_checks(records, protocol, role, expected_generation_signature):
    """Rebuild the shared evaluator signature for this entire content ensemble."""
    environment, source = mc._environment(), mc._source_hash()
    signature = digest({'schema': mc.CHECKPOINT_SCHEMA, 'engine_version': mc.ENGINE_VERSION,
                        'source_sha256': source, 'environment': environment, 'protocol': protocol,
                        'portfolio_hashes': sorted({record['content_sha256'] for record in records})})
    forbidden = {r['generation']['seed'] for r in records} | {r['generation']['pool_seed'] for r in records}
    require(protocol['seed'] not in forbidden, 'MC seed reused by generation or pool')
    common_stream, common_generation = None, expected_generation_signature
    for record in records:
        evaluation, simulation = _role_payload(record, role)
        require(evaluation['role'] == role and evaluation['method'] == 'monte_carlo'
                and evaluation.get('replayed') is True and evaluation.get('common_draws') is True, 'evaluation role/common-engine declaration differs')
        require(evaluation['protocol'] == protocol and simulation['protocol_sha256'] == digest(protocol), 'MC protocol differs')
        require(type(evaluation['draws']) is int and type(simulation['draws']) is int
                and evaluation['draws'] == simulation['draws'] == protocol['draws'], 'MC sample is incomplete or differs')
        require(evaluation['seed'] == simulation['seed'] == protocol['seed'], 'MC seed differs')
        require(simulation.get('independent_of_generation') is True and simulation.get('same_draws_for_all') is True, 'MC independence/common draws missing')
        require(evaluation['content_sha256'] == simulation['content_sha256'] == content_hash(record['grids']), 'MC bound to another content')
        for payload in (evaluation, simulation):
            require(payload['engine_version'] == mc.ENGINE_VERSION and payload['source_sha256'] == source, 'MC source/version differs from shared engine')
            require(payload['environment'] == environment, 'MC environment differs from current shared engine')
        stream = simulation['draw_stream_sha256']
        require(isinstance(stream, str) and len(stream) == 64 and all(c in '0123456789abcdef' for c in stream), 'MC stream SHA invalid')
        require(evaluation['draw_stream_sha256'] == stream, 'evaluation/simulation draw streams differ')
        common_stream = stream if common_stream is None else common_stream
        require(stream == common_stream, 'MC draw stream differs across MAIN and controls')
        generation_signature = evaluation['source_generation_signature']
        require(isinstance(generation_signature, str) and len(generation_signature) == 64
                and all(c in '0123456789abcdef' for c in generation_signature), 'source generation signature invalid')
        common_generation = generation_signature if common_generation is None else common_generation
        require(generation_signature == common_generation, 'MC belongs to another generation checkpoint')
        fingerprint = digest({'content_sha256': record['content_sha256'], 'signature': signature,
                              'draw_stream_sha256': stream})
        require(simulation['evaluation_sha256'] == fingerprint and evaluation['id'] == 'evaluation:' + fingerprint,
                'MC fingerprint belongs to another evaluated ensemble or content')
        metrics = simulation['metrics']
        require(set(metrics) == set(mc.EVENTS), 'MC events missing or unknown')
        counts = {}
        for event in mc.EVENTS:
            value = metrics[event]
            count = value['count']
            require(type(count) is int and 0 <= count <= protocol['draws'], 'MC counter invalid')
            require(_finite(value['probability']) and abs(value['probability'] - count / protocol['draws']) <= 1e-12,
                    'MC probability differs from counter')
            interval = value['ci95_wilson']
            require(isinstance(interval, list) and len(interval) == 2 and all(_finite(x) for x in interval)
                    and all(abs(a - b) <= 1e-12 for a, b in zip(interval, mc._wilson(count, protocol['draws']))), 'marginal Wilson interval differs')
            counts[event] = count
        require(counts['multiple_prizes'] <= counts['any_prize']
                and counts['at_least_4_numbers'] <= counts['at_least_3_numbers'] <= counts['any_prize'], 'MC event counts inconsistent')
        mean = simulation['mean_winning_grids']
        require(_finite(mean), 'winning-grid mean invalid')
        total = mean * protocol['draws']
        require(abs(total - round(total)) <= 1e-8
                and counts['any_prize'] + counts['multiple_prizes'] <= round(total)
                <= counts['any_prize'] + (len(record['grids']) - 1) * counts['multiple_prizes'], 'winning-grid mean inconsistent')
        exact = mc.exact_analytics(record['grids'])
        require(all(_finite(simulation[key]) and abs(simulation[key] - value) <= 1e-12
                    for key, value in exact.items()), 'analytic values differ from shared engine')
        if role == 'confirmation':
            old = record['evaluation']
            require(evaluation.get('independent_of_comparison') is True and protocol['seed'] != old['seed']
                    and stream != old['draw_stream_sha256'], 'confirmation reuses comparison seed/stream')
    return {'protocol': protocol, 'draw_stream_sha256': common_stream,
            'source_generation_signature': common_generation, 'evaluation_signature': signature,
            'source_sha256': source, 'engine_version': mc.ENGINE_VERSION, 'environment': environment}


def qualify_controls(main_records, control_records, experiment_kind, *, require_evaluation=True,
                     role='comparison', require_full_domain=False, expected_protocol=None,
                     expected_generation_signature=None):
    """Return qualified/missing/refused plus explicit cohort reasons; no draws."""
    require(experiment_kind in ('ablation', 'evolution') and role in ('comparison', 'confirmation'), 'unknown experiment/evaluation role')
    require(isinstance(main_records, list) and isinstance(control_records, list), 'record lists required')
    cohorts = [{'role': name, 'status': 'qualified', 'main_ids': [r.get('id') if isinstance(r, dict) else None for r in main_records],
                'control_ids': [], 'reference_count': 0, 'expected_count': CONTROL_COUNT, 'reasons': []} for name in ROLES]
    report = {'version': VERSION, 'status': 'qualified', 'experiment_kind': experiment_kind,
              'role': role, 'evaluation_required': require_evaluation, 'cohorts': cohorts, 'reasons': []}
    controls = {name: [] for name in ROLES}
    try:
        require(bool(main_records), 'MAIN records are missing')
        require(all(isinstance(r, dict) for r in main_records + control_records), 'record must be an object')
        for record in control_records:
            metadata = record.get('reference_benchmark', {})
            require(isinstance(metadata, dict) and metadata.get('role') in ROLES, 'control has missing or undeclared pool role')
            controls[metadata['role']].append(record)
        for cohort in cohorts:
            rows = controls[cohort['role']]
            cohort.update(control_ids=[r.get('id') for r in rows], reference_count=len(rows))
            if not rows and cohort['role'] == 'full_domain' and not require_full_domain:
                cohort['status'] = 'not_requested'
        physical = _physical(main_records[0])
        declared = _protocol(main_records[0]['constraint_profile'])
        protocol = mc._protocol(expected_protocol) if expected_protocol is not None else declared
        ids = [r['id'] for r in main_records + control_records]
        require(len(set(ids)) == len(ids), 'record context ids are repeated')
        factors = defaultdict(set)
        for record in main_records:
            require(_physical(record) == physical, 'MAIN physical cohorts differ')
            require('reference_benchmark' not in record, 'control supplied among MAIN records')
            require(_protocol(record['constraint_profile']) == declared, 'MAIN declared comparison protocols differ')
            if experiment_kind == 'ablation':
                weight, seed = _factor(record)
                require(seed not in factors[weight], 'ablation has a duplicated weight/seed')
                factors[weight].add(seed)
        if role == 'comparison':
            require(declared == protocol, 'requested comparison differs from executed profile protocol')
        for record in control_records:
            _control(record, _physical(record), {'physical': physical, 'protocol': declared})
        control_ids = {r['id'] for r in control_records}
        for record in main_records:
            params = record.get('lineage', {}).get('parameters', {})
            require(not control_ids.intersection(params.get('parent_context_ids', [])), 'control used as an evolutionary parent')
        for cohort in cohorts:
            rows = controls[cohort['role']]
            cohort.update(control_ids=[r['id'] for r in rows], reference_count=len(rows), physical=physical)
            if cohort['role'] == 'full_domain':
                cohort['physical'] = dict(physical, pool_numbers=list(range(1, 51)), pool_stars=list(range(1, 13)))
            if not rows and cohort['role'] == 'full_domain' and not require_full_domain:
                cohort['status'] = 'not_requested'
                continue
            if len(rows) != CONTROL_COUNT:
                cohort['status'] = 'missing' if len(rows) < CONTROL_COUNT else 'refused'
                cohort['reasons'].append({'code': 'reference_count', 'message': f'{len(rows)} controls present; {CONTROL_COUNT} required'})
            seeds = [r['generation']['seed'] for r in rows]
            require(len(set(seeds)) == len(seeds), 'control generation seeds are repeated within a role')
            if experiment_kind == 'ablation' and cohort['role'] == 'same_pool' and len(rows) == CONTROL_COUNT:
                require(len(factors) >= 2 and all(values == set(seeds) for values in factors.values()),
                        'ablation MAIN and RANDOM generation seeds are not paired/rectangular')
        if require_evaluation and all(c['status'] in ('qualified', 'not_requested') for c in cohorts):
            evaluated_main = main_records if role == 'comparison' else [r for r in main_records if 'confirmation' in r]
            missing = role == 'confirmation' and (not evaluated_main or any('confirmation' not in r for r in control_records)
                       or any('confirmation' not in r for r in main_records if r.get('is_finalist') is True))
            if missing:
                for cohort in cohorts:
                    if cohort['status'] == 'qualified':
                        cohort['status'] = 'missing'
                        cohort['reasons'].append({'code': 'missing_confirmation', 'message': 'MAIN finalist or control confirmation is missing'})
                report['status'] = 'missing'
                return report
            if role == 'confirmation' and expected_protocol is None:
                protocol = mc._protocol(evaluated_main[0]['confirmation']['evaluation']['protocol'])
            report['evaluation'] = _mc_checks(evaluated_main + control_records, protocol, role, expected_generation_signature)
    except (ValueError, KeyError, TypeError, IndexError, OverflowError) as exc:
        reason = {'code': 'incompatible_records', 'message': str(exc)}
        report['reasons'].append(reason)
        for cohort in cohorts:
            if cohort['status'] != 'not_requested':
                cohort['status'] = 'refused'
                cohort['reasons'].append(reason)
    statuses = {c['status'] for c in cohorts}
    report['status'] = 'refused' if 'refused' in statuses or report['reasons'] else 'missing' if 'missing' in statuses else 'qualified'
    return report


def _stats(values):
    if all(value is None for value in values):
        return {'n': len(values), 'mean': None, 'min': None, 'max': None, 'sd': None,
                'sd_method': 'population_across_generation_seeds'}
    require(values and all(_finite(value) for value in values), 'invalid measured series')
    return {'n': len(values), 'mean': fmean(values), 'min': min(values), 'max': max(values),
            'sd': pstdev(values), 'sd_method': 'population_across_generation_seeds'}


def _summary(rows):
    out = {}
    for key in rows[0]:
        values = [row[key] for row in rows]
        if isinstance(values[0], list):
            require(all(isinstance(value, list) and len(value) == len(values[0]) for value in values), 'vector lengths differ')
            out[key] = {'type': 'vector', 'length': len(values[0]),
                        'values': [_stats([value[i] for value in values]) for i in range(len(values[0]))]}
        else:
            out[key] = _stats(values)
    return out


def _subtract(left, right):
    return {key: [a - b for a, b in zip(value, right[key])] if isinstance(value, list)
            else None if value is None else value - right[key] for key, value in left.items()}


def _means(summary):
    return {key: [cell['mean'] for cell in value['values']] if value.get('type') == 'vector'
            else value['mean'] for key, value in summary.items()}


def _measure(record):
    geometry = portfolio_geometry(record['grids'], 50)
    values = metric_values(record['grids'], geometry, record['simulation'])
    values['portfolio.jackpot_probability@v1'] = mc.exact_analytics(record['grids'])['jackpot_probability']
    return values


def benchmark(main_records, control_records, experiment_kind, main_analysis=None, *,
              require_full_domain=False, expected_protocol=None, expected_confirmation_protocol=None,
              expected_generation_signature=None):
    """Describe only qualified common-lot MC; never infer a difference test."""
    comparison = qualify_controls(main_records, control_records, experiment_kind,
                                  require_full_domain=require_full_domain, expected_protocol=expected_protocol,
                                  expected_generation_signature=expected_generation_signature)
    confirmation = qualify_controls(main_records, control_records, experiment_kind, role='confirmation',
                                    require_full_domain=require_full_domain, expected_protocol=expected_confirmation_protocol,
                                    expected_generation_signature=expected_generation_signature)
    require(comparison['status'] == confirmation['status'] == 'qualified',
            'controlled publication refused: ' + str({'comparison': comparison, 'confirmation': confirmation}))
    require(comparison['evaluation']['source_generation_signature'] == confirmation['evaluation']['source_generation_signature'],
            'confirmation and comparison refer to different generation checkpoints')
    measurements = {r['id']: _measure(r) for r in main_records + control_records}
    controls = {name: [r for r in control_records if r['reference_benchmark']['role'] == name] for name in ROLES}
    random_rows = controls['same_pool']
    random_summary = _summary([measurements[r['id']] for r in random_rows])
    random_by_seed = {r['generation']['seed']: r for r in random_rows}
    groups = defaultdict(list)
    for record in main_records:
        key = _factor(record)[0] if experiment_kind == 'ablation' else (
            0 if record.get('is_starting_parent') is True else record['generation']['generation_index'])
        groups[key].append(record)
    main_groups, paired = [], []
    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda r: (r['generation']['seed'], r['id']))
        summary = _summary([measurements[r['id']] for r in rows])
        group = {'group_id': ('weight:' if experiment_kind == 'ablation' else 'generation:') + str(key),
                 'main_ids': [r['id'] for r in rows], 'n': len(rows), 'summary': summary,
                 'mean_differences': _subtract(_means(summary), _means(random_summary))}
        group['weight' if experiment_kind == 'ablation' else 'generation_index'] = key
        main_groups.append(group)
        if experiment_kind == 'ablation':
            differences = [{'seed': r['generation']['seed'], 'main_id': r['id'],
                            'random_id': random_by_seed[r['generation']['seed']]['id'],
                            'metrics': _subtract(measurements[r['id']], measurements[random_by_seed[r['generation']['seed']]['id']])}
                           for r in rows]
            paired.append({'weight': key, 'n': len(differences), 'rows': differences,
                           'summary': _summary([row['metrics'] for row in differences])})
    same_pool = {'role': 'comparison', 'pool_role': 'same_pool', 'paired': experiment_kind == 'ablation',
                 'orientation': 'main_minus_random', 'control_ids': [r['id'] for r in random_rows],
                 'reference_summary': random_summary, 'main_groups': main_groups, 'paired_differences': paired}
    full_domain = {'role': 'comparison', 'pool_role': 'full_domain', 'status': 'not_requested', 'control_ids': []}
    if controls['full_domain']:
        full = controls['full_domain']
        full_by_seed = {r['generation']['seed']: r for r in full}
        full_domain.update(status='qualified', control_ids=[r['id'] for r in full],
                           reference_summary=_summary([measurements[r['id']] for r in full]))
        aligned = set(random_by_seed) == set(full_by_seed)
        pool_rows = [{'seed': seed, 'same_pool_id': random_by_seed[seed]['id'], 'full_domain_id': full_by_seed[seed]['id'],
                      'metrics': _subtract(measurements[random_by_seed[seed]['id']], measurements[full_by_seed[seed]['id']])}
                     for seed in sorted(random_by_seed)] if aligned else []
        full_domain['pool_effect'] = {'paired': aligned, 'orientation': 'same_pool_random_minus_full_domain_random',
                                      'rows': pool_rows, 'summary': _summary([r['metrics'] for r in pool_rows]) if pool_rows else {},
                                      'mean_differences': _subtract(_means(random_summary), _means(full_domain['reference_summary']))}
    return {'version': VERSION, 'status': 'qualified', 'experiment_kind': experiment_kind,
            'qualification': {'comparison': comparison, 'confirmation': confirmation},
            'same_pool': same_pool, 'full_domain': full_domain,
            'limitations': [
                'Exact geometry is recomputed from grids; RANDOM controls never participate in parent or survivor selection.',
                'MAIN minus RANDOM differences are descriptive. Evolution groups are not paired with controls having different generation seeds.',
                'Population SD, minimum and maximum describe variation across constructions, not Monte-Carlo confidence intervals.',
                'Wilson intervals are marginal for individual event probabilities. Without per-draw covariance, no significance test or confidence interval for a difference is calculated.',
                'The full-domain RANDOM group is separate: its contrast with same-pool RANDOM also changes the pool.',
                'Summaries describe the comparison lot only. Independent confirmation covers selected MAIN finalists and every requested RANDOM control, and remains available on each record.',
            ]}
