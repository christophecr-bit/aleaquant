"""Contrat opérationnel 1.0, limité explicitement à EuroMillions sans options.

Les validations restent actives sous python -O. Aucun historique n'est lu.
"""
from copy import deepcopy
from decimal import Decimal
from itertools import combinations
from math import comb
from pathlib import Path
import random

from portfolio_import import content_hash, digest, load_json, require, validate_schema, values

VERSION = 'aleaquant-portfolio-pipeline-1.1'
EVENTS = ['any_prize', 'multiple_prizes', 'at_least_3_numbers', 'at_least_4_numbers']


def obj(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def integer(low, high):
    return {'type': 'integer', 'minimum': low, 'maximum': high}


def number(low=0, high=100):
    return {'type': 'number', 'minimum': low, 'maximum': high}


def seq(item, low=0, high=100):
    return {'type': 'array', 'items': item, 'minItems': low, 'maxItems': high}


def choice(*options):
    return {'type': 'string', 'enum': list(options)}


GUARANTEE_SCHEMA = obj({
    'pool_good_numbers': integer(0, 5), 'pool_good_stars': integer(0, 2),
    'condition_mode': choice('exactly'), 'required_numbers': integer(0, 5),
    'required_stars': integer(0, 2), 'threshold_mode': choice('at_least')})
SCHEMA = obj({
    'schema_version': {'type': 'string', 'const': '1.0'},
    'id': {'type': 'string', 'pattern': r'[A-Za-z][A-Za-z0-9_-]{0,79}'},
    'version': integer(1, 100000),
    'family': choice('RANDOM', 'BALANCED', 'LOW_OVERLAP', 'COVERAGE', 'CONCENTRATED'),
    'game': obj({'id': choice('euromillions'), 'rule_id': choice('euromillions-50-12-v1'),
                 'number_domain': dict(seq(integer(1, 50), 2, 2), const=[1, 50]),
                 'star_domain': dict(seq(integer(1, 12), 2, 2), const=[1, 12]),
                 'numbers_per_grid': dict(integer(5, 5), const=5),
                 'stars_per_grid': dict(integer(2, 2), const=2),
                 'unit_price_eur': dict(number(2.5, 2.5), const=2.5),
                 'options': seq({'type': 'string'}, 0, 0)}),
    'pool': obj({'method': choice('explicit', 'seeded_sample'),
                 'numbers': seq(integer(1, 50), 0, 50),
                 'stars': seq(integer(1, 12), 0, 12),
                 'number_count': integer(5, 50), 'star_count': integer(2, 12),
                 'seed': integer(0, 2**32-1)}),
    'constraints': obj({'grid_count': integer(1, 200), 'budget_max_eur': number(2.5, 100000),
                        'unique_grids': {'type': 'boolean', 'const': True},
                        'max_pairwise_overlap': obj({'numbers': integer(0, 5), 'stars': integer(0, 2)}),
                        'conditional_guarantee': {}}),
    'objectives': obj({'distinct_pairs': number(), 'distinct_triples': number(),
                       'balance_numbers': number(), 'balance_stars': number(),
                       'concentration': number(),
                       'minimize_overlap': obj({'aggregation': choice('sum_squares'),
                                                'numbers': number(), 'stars': number()})}),
    'search': obj({'method': choice('random', 'greedy', 'enumerate', 'prototype_greedy'),
                   'seed': integer(0, 2**32-1), 'candidate_count': integer(1, 20),
                   'candidates_per_step': integer(1, 2000), 'max_attempts': integer(1, 1000000),
                   'max_seconds': number(0.001, 60), 'population_size': dict(integer(1, 1), const=1),
                   'operators': seq({'type': 'string'}, 0, 0)}),
    'evaluation': obj({'method': choice('monte_carlo'), 'draws': integer(1, 1000000),
                       'seed': integer(0, 2**32-1), 'batch_size': integer(1, 10000),
                       'max_seconds': number(0.001, 60), 'max_certificate_cases': integer(1, 100000),
                       'metrics': dict(seq({'type': 'string'}, 4, 4), const=EVENTS)})})


def resolve_pool(profile):
    pool = profile['pool']
    if pool['method'] == 'explicit':
        return sorted(pool['numbers']), sorted(pool['stars'])
    rng = random.Random(pool['seed'])
    return sorted(rng.sample(range(1, 51), pool['number_count'])), sorted(rng.sample(range(1, 13), pool['star_count']))


def validate_profile(profile):
    validate_schema(profile, SCHEMA)
    c, search, evaluation, pool = (profile[k] for k in ('constraints', 'search', 'evaluation', 'pool'))
    if pool['method'] == 'explicit':
        values(pool['numbers'], pool['number_count'], 50, 'pool.numbers')
        values(pool['stars'], pool['star_count'], 12, 'pool.stars')
    else:
        require(pool['numbers'] == [] and pool['stars'] == [], 'pool : les listes doivent être vides pour seeded_sample')
    budget = Decimal(str(c['budget_max_eur']))
    require(budget == budget.quantize(Decimal('.01')), 'budget maximal : centimes entiers requis')
    require(Decimal(c['grid_count']) * Decimal('2.5') <= budget, 'budget maximal insuffisant pour le nombre de grilles')
    capacity = comb(pool['number_count'], 5) * comb(pool['star_count'], 2)
    require(c['grid_count'] <= capacity, 'capacité combinatoire insuffisante : impossibilité démontrée par comptage')
    require(evaluation['seed'] not in (pool['seed'], search['seed']), 'la graine d’évaluation doit être indépendante des graines de génération/pool')
    require(search['seed'] + search['candidate_count'] <= 2**32-1, 'graines candidates hors limites')
    if search['method'] == 'enumerate':
        require(c['grid_count'] == capacity, 'enumerate exige tout le pool dans le budget déclaré')
    if search['method'] in ('random', 'enumerate'):
        o = profile['objectives']
        require(all(o[k] == 0 for k in o if k != 'minimize_overlap') and
                o['minimize_overlap']['numbers'] == o['minimize_overlap']['stars'] == 0,
                'objectifs non nuls non pris en charge par random/enumerate')
    if search['method'] == 'prototype_greedy':
        o = profile['objectives']
        require(o['concentration'] == 0 and o['minimize_overlap']['stars'] == 0,
                'prototype_greedy ne prend pas en charge concentration ni pénalité overlap étoiles')
        require(search['candidate_count'] == 1, 'prototype_greedy exige une construction par graine')
        require(search['candidates_per_step'] == 1200, 'prototype_greedy exige 1200 propositions par étape')
        require(search['max_attempts'] >= c['grid_count'] * 1200,
                'prototype_greedy : max_attempts doit couvrir toutes les fenêtres de 1200 propositions')
        require(search['seed'] not in (pool['seed'], evaluation['seed']),
                'prototype_greedy exige une graine de construction distincte du pool et de l’évaluation')
    require(profile['family'] != 'RANDOM' or search['method'] == 'random', 'famille RANDOM exige la méthode random')
    guarantee = c['conditional_guarantee']
    if guarantee is not None:
        validate_schema(guarantee, GUARANTEE_SCHEMA, '$.constraints.conditional_guarantee')
        nums, stars = resolve_pool(profile)
        x, y = guarantee['pool_good_numbers'], guarantee['pool_good_stars']
        cases = comb(len(nums), x)*comb(50-len(nums), 5-x)*comb(len(stars), y)*comb(12-len(stars), 2-y)
        require(cases > 0, 'condition de garantie impossible : aucune issue sous ces hypothèses')
        require(cases <= evaluation['max_certificate_cases'] and cases*c['grid_count'] <= 2000000,
                'garantie demandée : preuve hors des limites d’énumération prises en charge')
    if c['grid_count'] > 1:
        require(pool['number_count'] >= 10-c['max_pairwise_overlap']['numbers'],
                'max_pairwise_overlap.numbers impossible pour deux grilles dans ce pool')
        require(pool['star_count'] >= 4-c['max_pairwise_overlap']['stars'],
                'max_pairwise_overlap.stars impossible pour deux grilles dans ce pool')


def validate_grids(grids, profile):
    """Retourne les violations contrôlables ; la garantie est vérifiée séparément."""
    errors = []
    try:
        require(isinstance(grids, list) and len(grids) == profile['constraints']['grid_count'], 'nombre de grilles incompatible')
        nums, stars = resolve_pool(profile)
        for i, grid in enumerate(grids):
            require(isinstance(grid, list) and len(grid) == 2, f'grille {i+1} : deux composantes requises')
            values(grid[0], 5, 50, f'grille {i+1} numéros')
            values(grid[1], 2, 12, f'grille {i+1} étoiles')
            require(set(grid[0]) <= set(nums) and set(grid[1]) <= set(stars), f'grille {i+1} hors pool')
        require(len({(tuple(sorted(g[0])),tuple(sorted(g[1]))) for g in grids}) == len(grids), 'grilles répétées')
        limit = profile['constraints']['max_pairwise_overlap']
        for a,b in combinations(grids,2):
            require(len(set(a[0]) & set(b[0])) <= limit['numbers'], 'intersection maximale de numéros dépassée')
            require(len(set(a[1]) & set(b[1])) <= limit['stars'], 'intersection maximale d’étoiles dépassée')
        require(Decimal(len(grids))*Decimal('2.5') <= Decimal(str(profile['constraints']['budget_max_eur'])), 'budget dépassé')
    except (ValueError, TypeError, KeyError) as exc:
        errors.append(str(exc))
    return errors


def load_profiles(path):
    bundle = load_json(Path(path).read_bytes())
    require(isinstance(bundle, dict) and set(bundle) == {'schema_version', 'profiles'}, 'registre : schema_version et profiles requis, sans autres champs')
    require(bundle['schema_version'] == '1.0' and isinstance(bundle['profiles'], list) and 1 <= len(bundle['profiles']) <= 100, 'registre de profils 1.0 invalide')
    profiles = bundle['profiles']
    for p in profiles:
        validate_profile(p)
    require(len({p['id'] for p in profiles}) == len(profiles), 'identifiants de profils répétés')
    protocol = profiles[0]['evaluation']
    require(all(p['evaluation'] == protocol for p in profiles), 'une exécution comparative exige un protocole d’évaluation commun')
    seeds = {p['pool']['seed'] for p in profiles}
    for p in profiles:
        seeds.update(range(p['search']['seed'], p['search']['seed']+p['search']['candidate_count']+1))
    require(protocol['seed'] not in seeds, 'évaluation indépendante : graine réutilisée par un profil')
    return profiles


def schema_document():
    schema = deepcopy(SCHEMA)
    schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema', '$id':'aleaquant-portfolio-profile-1.0'})
    schema['properties']['constraints']['properties']['conditional_guarantee'] = {'oneOf':[{'type':'null'},GUARANTEE_SCHEMA]}
    return schema
