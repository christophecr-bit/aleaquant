"""Import borné du prototype 0.1 ; aucun code archivé ni Monte-Carlo exécuté.

Les grilles, la géométrie et les garanties sont vérifiées indépendamment.
Les comptages Monte-Carlo restent des preuves importées, jamais requalifiées
en probabilités exactes. Le dictionnaire de grilles du site reste inchangé.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from itertools import combinations
import json
import math
from pathlib import Path
import re
import sys
import zipfile

import numpy as np

from portfolio_geometry import portfolio_geometry

ENGINE_VERSION = 'aleaquant-portfolio-import-v1'
ROOT = Path(__file__).resolve().parents[1]
TOTAL = math.comb(50, 5) * math.comb(12, 2)
EVENTS = ('any_prize', 'multiple_prizes', 'at_least_3_numbers', 'at_least_4_numbers')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def is_number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def content_hash(grids):
    canonical = sorted([[sorted(g[0]), sorted(g[1])] for g in grids])
    return digest({'rule_id': 'euromillions-50-12-v1', 'grids': canonical})


def load_json(raw):
    def pairs(items):
        out = {}
        for name, value in items:
            require(name not in out, f'clé JSON répétée : {name}')
            out[name] = value
        return out
    def constant(value):
        raise ValueError(f'nombre JSON non fini : {value}')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def validate_schema(value, schema, path='$'):
    """Sous-ensemble explicitement utilisé du schéma JSON versionné local."""
    kind = schema.get('type')
    valid = {
        'object': isinstance(value, dict), 'array': isinstance(value, list),
        'string': isinstance(value, str), 'boolean': type(value) is bool,
        'integer': type(value) is int,
        'number': is_number(value),
    }
    if kind:
        require(valid[kind], f'{path} : type {kind} attendu')
    if 'const' in schema:
        require(type(value) is type(schema['const']) and value == schema['const'],
                f'{path} : valeur attendue {schema["const"]!r}')
    if 'enum' in schema:
        require(value in schema['enum'], f'{path} : valeur inconnue')
    if kind in ('integer', 'number'):
        require(value >= schema.get('minimum', -math.inf), f'{path} : valeur trop petite')
        require(value <= schema.get('maximum', math.inf), f'{path} : valeur trop grande')
    if kind == 'string' and 'pattern' in schema:
        require(re.fullmatch(schema['pattern'], value) is not None, f'{path} : identifiant invalide')
    if kind == 'array':
        require(len(value) >= schema.get('minItems', 0), f'{path} : liste trop courte')
        require(len(value) <= schema.get('maxItems', math.inf), f'{path} : liste trop longue')
        for i, item in enumerate(value):
            validate_schema(item, schema['items'], f'{path}[{i}]')
    if kind == 'object':
        properties = schema['properties']
        require(set(schema.get('required', ())) <= value.keys(), f'{path} : champs obligatoires manquants')
        if schema.get('additionalProperties') is False:
            require(value.keys() <= properties.keys(), f'{path} : champs inconnus {sorted(value.keys() - properties.keys())}')
        for name, item in value.items():
            if name in properties:
                validate_schema(item, properties[name], f'{path}.{name}')


def validate_config(config):
    schema = load_json((Path(__file__).with_name('portfolio_profiles.schema.json')).read_bytes())
    validate_schema(config, schema)
    ids = [p['id'] for p in config['profiles']]
    require(len(ids) == len(set(ids)), 'identifiants de profils répétés')
    for p in config['profiles']:
        c = p['constraints']
        m, v, s = c['grid_count'], c['pool_number_count'], c['pool_star_count']
        capacity = math.comb(v, 5) * math.comb(s, 2)
        require(m * config['unit_price_eur'] <= c['budget_max_eur'], f'{p["id"]} : budget dépassé')
        require(m <= capacity, f'{p["id"]} : capacité combinatoire insuffisante')
        if p['family'] == 'Complete':
            require(m == capacity, f'{p["id"]} : Complete doit énumérer tout le pool')
        if p['family'] == 'Clustered':
            require(m <= math.comb(v - 3, 2) * math.comb(s, 2), f'{p["id"]} : capacité du noyau insuffisante')


def values(part, size, domain, name):
    require(isinstance(part, list) and len(part) == size, f'{name} : cardinalité invalide')
    require(all(type(x) is int and 1 <= x <= domain for x in part), f'{name} : domaine invalide')
    require(len(set(part)) == len(part), f'{name} : valeurs répétées')


def close(actual, expected, name):
    require(is_number(actual) and abs(actual) <= max(1, abs(expected)) * 10
            and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12),
            f'{name} : résultat incompatible')


def certify(grids, pool_numbers, pool_stars, max_cases=100000):
    require(type(max_cases) is int and max_cases > 0, 'plafond de certification invalide')
    require(isinstance(pool_numbers, list) and 5 <= len(pool_numbers) <= 50, 'pool numéros invalide')
    require(isinstance(pool_stars, list) and 2 <= len(pool_stars) <= 12, 'pool étoiles invalide')
    values(pool_numbers, len(pool_numbers), 50, 'pool numéros')
    values(pool_stars, len(pool_stars), 12, 'pool étoiles')
    require(isinstance(grids, list) and 1 <= len(grids) <= 2000, 'nombre de grilles invalide')
    for g in grids:
        require(isinstance(g, list) and len(g) == 2, 'format grille invalide')
        values(g[0], 5, 50, 'grille numéros')
        values(g[1], 2, 12, 'grille étoiles')
        require(set(g[0]) <= set(pool_numbers) and set(g[1]) <= set(pool_stars), 'grille hors pool')
    require(len({(tuple(sorted(g[0])), tuple(sorted(g[1]))) for g in grids}) == len(grids), 'grilles répétées')
    cases = math.comb(len(pool_numbers), 5) * math.comb(len(pool_stars), 2)
    require(cases <= max_cases, 'plafond de cas de certification dépassé')
    require(cases * len(grids) <= 2_000_000, 'plafond de travail de certification dépassé')
    ns = list(combinations(pool_numbers, 5))
    number_sets = [set(g[0]) for g in grids]
    star_sets = [set(g[1]) for g in grids]
    nc = np.array([[len(set(d) & g) for g in number_sets] for d in ns], dtype=np.int8)
    guaranteed = {str(s): 5 for s in range(3)}
    for stars in combinations(pool_stars, 2):
        hits = np.array([len(set(stars) & g) for g in star_sets])
        for s in range(3):
            best = np.where(hits[None, :] >= s, nc, -1).max(axis=1)
            guaranteed[str(s)] = min(guaranteed[str(s)], int(best.min()))
    return {'method': 'exhaustive_enumeration', 'verification': 'independent_recalculation',
            'content_sha256': content_hash(grids),
            'condition': 'Les 5 numéros et les 2 étoiles tirés sont dans les pools indiqués ; les correspondances doivent être sur une même grille.',
            'cases': cases, 'minimum_best_numbers_by_required_stars': guaranteed,
            'condition_probability': cases / TOTAL}


def wilson(count, draws):
    z = 1.95996398454
    ph, den = count / draws, 1 + z * z / draws
    mid = (ph + z * z / (2 * draws)) / den
    half = z * math.sqrt(ph * (1 - ph) / draws + z * z / (4 * draws * draws)) / den
    return [mid - half, mid + half]


def validate_simulation(sim, config, m):
    draws = config['evaluation']['draws']
    require(sim['draws'] == draws and type(sim['draws']) is int, 'simulation : effectif incompatible')
    require(sim['seed'] == config['evaluation']['seed'] and type(sim['seed']) is int, 'simulation : graine incompatible')
    require(sim['independent_of_generation'] is True and sim['same_draws_for_all'] is True,
            'simulation : protocole partagé absent')
    require(set(sim['metrics']) == set(EVENTS), 'simulation : événements inconnus/manquants')
    for name in EVENTS:
        event = sim['metrics'][name]
        c = event['count']
        require(type(c) is int and 0 <= c <= draws, f'{name} : compte invalide')
        close(event['probability'], c / draws, name)
        require(len(event['ci95_wilson']) == 2, f'{name} : intervalle invalide')
        for actual, expected in zip(event['ci95_wilson'], wilson(c, draws)):
            close(actual, expected, f'{name} IC95')
    require(sim['metrics']['multiple_prizes']['count'] <= sim['metrics']['any_prize']['count'],
            'simulation : événements emboîtés incompatibles')
    require(sim['metrics']['at_least_4_numbers']['count'] <= sim['metrics']['at_least_3_numbers']['count'],
            'simulation : seuils emboîtés incompatibles')
    require(sim['metrics']['at_least_3_numbers']['count'] <= sim['metrics']['any_prize']['count'],
            'simulation : rang inclus incompatible')
    one = sum(math.comb(5, j) * math.comb(45, 5-j) / math.comb(50, 5) for j in range(2, 6))
    one += 5 * math.comb(45, 4) / TOTAL
    close(sim['theoretical_mean_winning_grids'], m * one, 'moyenne analytique')
    require(is_number(sim['mean_winning_grids']) and 0 <= sim['mean_winning_grids'] <= m,
            'simulation : moyenne invalide')
    any_prize = sim['metrics']['any_prize']['probability']
    multiple = sim['metrics']['multiple_prizes']['probability']
    mean = sim['mean_winning_grids']
    require(any_prize + multiple <= mean + 1e-12 and mean <= any_prize + (m - 1) * multiple + 1e-12,
            'simulation : moyenne incompatible avec les événements gagnants')
    require(abs(mean * draws - round(mean * draws)) < 1e-6,
            'simulation : moyenne non issue de comptes entiers')


def import_archive(archive_path, metrics_path, max_certificate_cases=100000):
    archive_path, metrics_path = Path(archive_path), Path(metrics_path)
    require(archive_path.stat().st_size <= 4_000_000, 'archive trop volumineuse')
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        require(len({i.filename for i in entries}) == len(entries), 'entrées ZIP répétées')
        expected = {'build.py', 'package_report.py', 'profiles.json', 'results.json',
                    'atlas.json', 'README.md', 'catalogue.html', 'validation.json'}
        require({i.filename for i in entries} == expected, 'contenu ZIP inattendu')
        require(sum(i.file_size for i in entries) <= 8_000_000, 'archive décompressée trop volumineuse')
        raw = {name: archive.read(name) for name in expected}
    config = load_json(raw['profiles.json'])
    validate_config(config)
    require(sum(math.comb(p['constraints']['grid_count'], 2) for p in config['profiles']) <= 2_000_000,
            'plafond de travail géométrique dépassé')
    results = load_json(raw['results.json'])
    atlas = load_json(raw['atlas.json'])
    require(results['schema_version'] == '0.1' and atlas['schema_version'] == '0.1', 'version résultats inconnue')
    require(results['config'] == config, 'configuration résultats différente')
    close(results['price_eur'], config['unit_price_eur'], 'prix unitaire')
    require(len(results['profiles']) == len(config['profiles']), 'profils manquants')
    source_profiles = {p['id']: p for p in results['profiles']}
    require(len(source_profiles) == len(config['profiles']), 'profils résultats répétés')
    require(set(source_profiles) == {p['id'] for p in config['profiles']}, 'profils résultats inattendus')
    nodes = atlas['nodes']
    require(len(nodes) == len(source_profiles) and not atlas['edges'], 'Atlas source initial incompatible')
    require(len({n['id'] for n in nodes}) == len(nodes), 'nœuds source répétés')
    require(all(n['type'] == 'portfolio' and n['data'] == source_profiles.get(n['id']) for n in nodes),
            'Atlas source différent des résultats')
    profiles, graph_nodes, edges = [], [], []
    families = {'Complete': 'COVERAGE', 'Balanced': 'BALANCED',
                'Spread': 'LOW_OVERLAP', 'Clustered': 'CONCENTRATED'}
    for spec in config['profiles']:
        p, c = source_profiles[spec['id']], spec['constraints']
        require(p['family'] == spec['family'] and type(p['profile_version']) is int
                and p['profile_version'] == 1, 'famille/version profil incompatible')
        values(p['pool_numbers'], c['pool_number_count'], 50, 'pool numéros')
        values(p['pool_stars'], c['pool_star_count'], 12, 'pool étoiles')
        m = c['grid_count']
        close(p['budget_eur'], m * config['unit_price_eur'], 'coût')
        require(p['constraints'] == {'grid_count': m, 'unique_grids': True, 'number_range': [1, 50],
                                     'star_range': [1, 12], 'numbers_per_grid': 5, 'stars_per_grid': 2},
                'contraintes résultats différentes')
        generation = p['generation']
        require(generation['seed'] == spec['search']['seed'] and generation['pool_seed'] == config['pool_seed']
                and generation['candidates_per_step'] == spec['search']['candidates_per_step']
                and generation['method'] == ('enumeration' if spec['family'] == 'Complete' else 'greedy_candidate_search'),
                'provenance de génération différente')
        require(p['lineage'] == {'node_id': spec['id'], 'parent_ids': [], 'operation': 'initial_generation'},
                'parents source inattendus')
        require(len(p['grids']) == m, 'nombre de grilles différent')
        grids = []
        for g in p['grids']:
            require(set(g) == {'numbers', 'stars'}, 'champs grille inconnus')
            values(g['numbers'], 5, 50, 'grille numéros')
            values(g['stars'], 2, 12, 'grille étoiles')
            require(set(g['numbers']) <= set(p['pool_numbers']) and set(g['stars']) <= set(p['pool_stars']),
                    'grille hors pool')
            grids.append([sorted(g['numbers']), sorted(g['stars'])])
        require(len({(tuple(g[0]), tuple(g[1])) for g in grids}) == m, 'grilles répétées')
        if spec['family'] == 'Clustered':
            require(len(set.intersection(*(set(g[0]) for g in grids))) >= 3, 'noyau Clustered absent')
        geometry = portfolio_geometry(grids, 50)
        exact = {'mean_number_overlap': geometry['overlap_mean'], 'max_number_overlap': geometry['overlap_max'],
                 'distinct_pairs': geometry['coverage'][2]['covered'], 'distinct_triples': geometry['coverage'][3]['covered'],
                 'distinct_star_pairs': geometry['second']['distinct_combinations'], 'jackpot_probability': m / TOTAL,
                 'number_frequencies': {str(n): sum(n in g[0] for g in grids) for n in p['pool_numbers']}}
        require(set(p['exact']) == set(exact), 'métriques exactes inconnues/manquantes')
        for name, value in exact.items():
            if isinstance(value, float):
                close(p['exact'][name], value, name)
            else:
                require(digest(p['exact'][name]) == digest(value), f'{name} : résultat incompatible')
        certificate = {'method': 'not_checked', 'condition': 'Aucune garantie conditionnelle certifiée.'}
        if len(p['pool_numbers']) <= 15:
            certificate = certify(grids, p['pool_numbers'], p['pool_stars'], max_certificate_cases)
            require(p['certificate']['method'] == 'exhaustive_enumeration'
                    and p['certificate']['cases'] == certificate['cases']
                    and p['certificate']['minimum_best_numbers_by_required_stars'] == certificate['minimum_best_numbers_by_required_stars'],
                    'certificat source incompatible')
            close(p['certificate']['condition_probability'], certificate['condition_probability'], 'condition du certificat')
        else:
            require(p['certificate']['method'] == 'not_checked', 'certificat non vérifiable dans ce protocole')
        validate_simulation(p['simulation'], config, m)
        content = content_hash(grids)
        protocol = {'method': 'imported_monte_carlo', 'draws': config['evaluation']['draws'],
                    'seed': config['evaluation']['seed'], 'common_draws': True,
                    'source_engine': 'archive-build.py', 'source_engine_sha256': sha256(raw['build.py']).hexdigest(),
                    'source_results_sha256': sha256(raw['results.json']).hexdigest(),
                    'environment': 'not_recorded_by_source'}
        evaluation_id = 'evaluation:' + digest({'content': content, 'protocol': protocol, 'simulation': p['simulation']})
        effective_profile = {'schema_version': config['schema_version'], 'game': config['game'],
                             'unit_price_eur': config['unit_price_eur'], 'pool_seed': config['pool_seed'],
                             'profile': spec}
        profile_id, portfolio_id = 'profile:' + digest(effective_profile), 'portfolio:' + content
        profiles.append({'id': p['id'], 'family': p['family'], 'display_family': families[p['family']],
                         'profile_version': 1, 'config_sha256': digest(effective_profile), 'content_sha256': content,
                         'game_id': 'euromillions', 'rule_id': 'euromillions-50-12-v1', 'format_id': '5of50+2of12',
                         'grid_count': m, 'budget_eur': p['budget_eur'], 'unit_price_eur': config['unit_price_eur'],
                         'pool_numbers': sorted(p['pool_numbers']), 'pool_stars': sorted(p['pool_stars']),
                         'grids': sorted(grids), 'geometry': geometry, 'exact': exact,
                         'certificate': certificate, 'simulation': p['simulation'], 'generation': generation,
                         'state': 'certified' if certificate['method'] == 'exhaustive_enumeration' else 'evaluated',
                         'state_scope': 'conditional_guarantee' if certificate['method'] == 'exhaustive_enumeration' else 'imported_evaluation',
                         'evaluation': dict(protocol, id=evaluation_id, content_sha256=content, replayed=False),
                         'lineage': {'profile_node_id': profile_id, 'portfolio_node_id': portfolio_id, 'parent_ids': []}})
        graph_nodes.extend([{'id': profile_id, 'type': 'profile', 'data': effective_profile},
                            {'id': portfolio_id, 'type': 'portfolio', 'content_sha256': content},
                            {'id': evaluation_id, 'type': 'evaluation_run', 'content_sha256': content, 'protocol': protocol}])
        edges.extend([{'type': 'generated_from', 'source': portfolio_id, 'target': profile_id},
                      {'type': 'evaluated_by', 'source': portfolio_id, 'target': evaluation_id}])
    metrics = load_json(metrics_path.read_bytes())
    require(isinstance(metrics, list) and all(isinstance(x, dict) and 'id' in x for x in metrics), 'dictionnaire Atlas invalide')
    require(len({x['id'] for x in metrics}) == len(metrics), 'identifiants de métriques répétés')
    cohorts = []
    for budget in sorted({p['budget_eur'] for p in profiles}):
        cohort = [p for p in profiles if p['budget_eur'] == budget]
        cohorts.append({'budget_eur': budget, 'grid_count': cohort[0]['grid_count'],
                        'profile_ids': [p['id'] for p in cohort], 'random_reference_available': False,
                        'comparison_status': 'exploratory_without_random_reference'})
    return {'schema': 'aleaquant-portfolio-pipeline-v1', 'engine_version': ENGINE_VERSION,
            'verification_environment': {'python': sys.version.split()[0], 'numpy': np.__version__},
            'source': {'date': results['date'], 'archive_name': archive_path.name,
                       'archive_sha256': sha256(archive_path.read_bytes()).hexdigest(),
                       'members_sha256': {name: sha256(data).hexdigest() for name, data in sorted(raw.items())}},
            'metric_source': {'path': 'metrics.json', 'sha256': sha256(metrics_path.read_bytes()).hexdigest(),
                              'definitions_count': len(metrics), 'scope': 'grid',
                              'portfolio_evaluator': 'engine/portfolio_geometry.py',
                              'portfolio_definitions': 'docs/ATLAS-GEOMETRIES-ARCHITECTURE.md'},
            'configuration_sha256': digest(config), 'profiles': profiles, 'cohorts': cohorts,
            'graph': {'nodes': list({n['id']: n for n in graph_nodes}.values()), 'edges': edges},
            'states': ['draft', 'invalid', 'feasible', 'evaluated', 'certified', 'search_exhausted', 'proven_infeasible'],
            'limitations': ['Monte-Carlo importé, non rejoué ; environnement source non enregistré.',
                            'Garanties conditionnelles sur une même grille ; 0+2 ne constitue pas un rang gagnant.',
                            'RANDOM absent de ces cohortes ; aucune supériorité ni optimalité établie.',
                            'Mutation, croisement, pools explicites, contrainte dure de recouvrement et reprise de recherche restent à implémenter.',
                            'Les budgets sont des alternatives ; aucun montant de gain ni remboursement estimé.'],
            'exclusions': results['exclusions']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--metrics', type=Path, default=ROOT / 'dist/metrics.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/data/portfolio_pipeline.json')
    parser.add_argument('--check', action='store_true', help='vérifier sans écrire')
    args = parser.parse_args(argv)
    try:
        result = import_archive(args.archive, args.metrics)
        if not args.check:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            tmp = args.output.with_suffix(args.output.suffix + '.tmp')
            tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
            tmp.replace(args.output)
        print(f'{len(result["profiles"])} portefeuilles, {sum(p["grid_count"] for p in result["profiles"])} grilles vérifiées ; Monte-Carlo non rejoué.')
        return 0
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
        print(f'Import refusé : {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
