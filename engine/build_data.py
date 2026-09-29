"""Moteur statistique V0 : historique + lois exactes -> données du site et facts.

Entrées (lecture seule) : base SQLite EuroMillions du laboratoire, lois exactes
(dist/data/exact_laws.json, voir exact_laws.py) et catalogues de portefeuilles.
Sorties dans dist/data :
  draws.json           une ligne compacte par tirage (métriques en clés de loi)
  laws.json            lois exactes vs historique + tests Lab (Monte-Carlo, BH)
  atlas.json           cooccurrences historiques + géométries de portefeuilles
  facts/<draw>.json    facts des derniers tirages ; facts/latest.json
  manifest.json        provenance : SHA des entrées, version du moteur, dates

Usage : python3 engine/build_data.py [--facts N] [--draw EM-26077]
"""
import argparse
import json
import math
import time
from collections import Counter
from itertools import combinations
from math import comb

import numpy as np

from common import (CURRENT_RULE, DATA, ENGINE_VERSION, HISTORY_DB, LAB, MAIN_CAT, MAIN_FIELDS,
                    STAR_FIELDS, key, load_draws, load_patterns, read_json, sha256_file, write_json)
from facts import LABELS, STAR_LABELS, build_draw_facts, build_indexes

SEED = 20260929
R = 2000


# ---------------------------------------------------------------- historique
def history_rows(draws, patterns):
    rows = []
    for d in draws:
        mp = patterns.main_pattern(d['main'])
        row = {'main': {f: key(mp[f]) for f in MAIN_FIELDS + MAIN_CAT}, 'rule': d['rule'],
               'signature': patterns.main_signature(mp), 'stars': None}
        if d['rule'] == CURRENT_RULE:
            sp = patterns.stars_pattern(d['stars'])
            row['stars'] = {f: key(sp[f]) for f in STAR_FIELDS}
        rows.append(row)
    return rows


# ---------------------------------------------------------------- lois + Lab
def wh_pvalue(x, df):
    if df <= 0:
        return 1.0
    z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    return 0.5 * math.erfc(z / math.sqrt(2))


def law_vs_history(law, total, observed_keys, numeric, rng):
    """Compare une loi exacte à l'historique. Monte-Carlo tiré de la loi exacte elle-même :
    pour une métrique isolée, tirer n valeurs iid de sa loi équivaut à tirer n grilles."""
    keys = sorted(law, key=(lambda k: float(k)) if numeric else (lambda k: -law[k]))
    probs = np.array([law[k] / total for k in keys])
    pos = {k: i for i, k in enumerate(keys)}
    n = len(observed_keys)
    obs = np.bincount([pos[k] for k in observed_keys], minlength=len(keys))
    # regroupement : effectif attendu >= 5
    groups, cur, e = [], [], 0.0
    for i in range(len(keys)):
        cur.append(i); e += probs[i] * n
        if e >= 5:
            groups.append(cur); cur, e = [], 0.0
    if cur:
        groups[-1] += cur
    gmap = np.zeros(len(keys), dtype=int)
    for g, members in enumerate(groups):
        gmap[members] = g
    gexp = np.bincount(gmap, weights=probs * n, minlength=len(groups))

    def chi(counts):
        o = np.bincount(gmap, weights=counts, minlength=len(groups))
        return float(((o - gexp) ** 2 / gexp).sum())

    x = chi(obs)
    sims = rng.multinomial(n, probs, size=R)
    sim_chi = np.array([chi(s) for s in sims])
    out = {'values': keys, 'p': probs.round(10).tolist(), 'observed': obs.tolist(), 'n': n,
           'chi2': round(x, 3), 'df': len(groups) - 1, 'p_chi2': (1 + int((sim_chi >= x).sum())) / (R + 1),
           'p_chi2_wh': wh_pvalue(x, len(groups) - 1)}
    if numeric:
        v = np.array([float(k) for k in keys])
        mu = float((v * probs).sum()); sd = float(math.sqrt(((v - mu) ** 2 * probs).sum()))
        om = float((v * obs).sum() / n); osd = float(math.sqrt(((v - om) ** 2 * obs).sum() / n))
        sm = sims @ v / n
        ssd = np.sqrt(np.maximum(sims @ (v ** 2) / n - sm ** 2, 0))
        med = float(np.median(ssd))
        out.update({'mean_th': mu, 'sd_th': sd, 'mean_obs': om, 'sd_obs': osd,
                    'p_mean': (1 + int((np.abs(sm - mu) >= abs(om - mu)).sum())) / (R + 1),
                    'p_sd': (1 + int((np.abs(ssd - med) >= abs(osd - med)).sum())) / (R + 1)})
    return out


def benjamini_hochberg(metrics):
    tests = [(r[t], mid, t) for mid, r in metrics.items() for t in ('p_chi2', 'p_mean', 'p_sd') if t in r]
    tests.sort()
    m, prev = len(tests), 1.0
    for rank in range(m, 0, -1):
        p, mid, t = tests[rank - 1]
        prev = min(prev, p * m / rank)
        metrics[mid]['q' + t[1:]] = prev
    return m


def build_laws(laws, draws, rows):
    rng = np.random.default_rng(SEED)
    out = {}
    for f in MAIN_FIELDS + MAIN_CAT:
        out['main.' + f] = law_vs_history(laws['main'][f], laws['main_total'],
                                          [r['main'][f] for r in rows], f not in MAIN_CAT, rng)
        out['main.' + f]['label'] = LABELS[f]
    era = [r for r in rows if r['stars']]
    for f in STAR_FIELDS:
        out['stars.' + f] = law_vs_history(laws['stars'][f], laws['stars_total'],
                                           [r['stars'][f] for r in era], True, rng)
        out['stars.' + f]['label'] = STAR_LABELS[f]
        out['stars.' + f]['era_from'] = '2016-09-27'
    n_tests = benjamini_hochberg(out)
    for f in MAIN_CAT:  # lois catégorielles : 20 classes les plus probables + reste
        r = out['main.' + f]
        if len(r['values']) > 21:
            r['values'] = r['values'][:20] + ['autres']
            r['p'] = r['p'][:20] + [round(1 - sum(r['p'][:20]), 10)]
            r['observed'] = r['observed'][:20] + [r['n'] - sum(r['observed'][:20])]
    return {'schema': 'aleaquant-laws-v1', 'engine': ENGINE_VERSION, 'monte_carlo_histories': R,
            'seed': SEED, 'tests': n_tests, 'correction': 'Benjamini-Hochberg',
            'n_draws': len(draws), 'n_star_era': len(era), 'metrics': out}


# ---------------------------------------------------------------- atlas
def cooccurrences(draws, rng):
    n = len(draws)
    co = Counter()
    freq = Counter()
    for d in draws:
        freq.update(d['main'])
        co.update(combinations(d['main'], 2))
    p = comb(48, 3) / comb(50, 5)
    expected, sd = n * p, math.sqrt(n * p * (1 - p))
    # distribution nulle du max |z| sur 1 225 paires (historiques uniformes simulés)
    null_max = []
    iu = np.triu_indices(50, 1)
    for _ in range(200):
        c = np.zeros((50, 50), dtype=int)
        for _d in range(n):
            g = np.sort(rng.choice(50, 5, replace=False))
            for a, b in combinations(g, 2):
                c[a, b] += 1
        null_max.append(float(np.abs((c[iu] - expected) / sd).max()))
    return {'n': n, 'expected': expected, 'sd': sd,
            'pairs': [[a, b, co[(a, b)]] for a in range(1, 51) for b in range(a + 1, 51)],
            'freq': [freq[i] for i in range(1, 51)], 'freq_expected': n / 10,
            'null_max_abs_z': {'median': float(np.median(null_max)), 'p95': float(np.percentile(null_max, 95)),
                               'histories': len(null_max)}}


def read_grids(path, sep='|'):
    grids = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        parts = [p.split() for p in line.split(sep)]
        grids.append([[int(x) for x in part] for part in parts])
    return grids


def portfolio_geometry(grids, domain):
    """Géométrie descriptive de la composante principale (identique au dictionnaire Atlas)."""
    sets = [frozenset(g[0]) for g in grids]
    k = len(grids[0][0])
    inter = [len(a & b) for a, b in combinations(sets, 2)]
    occ = Counter(v for s in sets for v in s)
    cov = {}
    for t in (2, 3):
        c = Counter(sub for g in grids for sub in combinations(sorted(g[0]), t))
        cov[t] = {'covered': len(c), 'possible': comb(domain, t),
                  'collisions': sum(comb(m, 2) for m in c.values())}
    return {'grids': len(grids), 'union': len(set().union(*sets)),
            'overlap_mean': sum(inter) / len(inter), 'overlap_max': max(inter),
            'overlap_hist': [inter.count(i) for i in range(k + 1)],
            'occurrence_sd': float(np.std([occ.get(v, 0) for v in range(1, domain + 1)])),
            'coverage': cov}


def portfolios():
    gens = []
    # EuroMillions : génération 1, 35 contenus évalués exactement sur 139 838 160 issues
    sel_path = LAB / 'reports' / 'euromillions_final_selection' / 'selection.json'
    if sel_path.exists():
        sel = read_json(sel_path)
        shortlist = {s['portfolio_id']: s.get('roles', []) for s in sel.get('shortlist', [])} \
            if isinstance(sel.get('shortlist'), list) else {}
        items = []
        for c in sel['candidates']:
            pid = c['portfolio_id']
            path = LAB / 'reports' / 'euromillions_portfolio_search' / 'portfolios' / (pid + '.txt')
            if not path.exists():
                continue
            grids = read_grids(path)
            ex = c['exact']
            items.append({
                'id': pid, 'family': c['family'], 'fronts': c.get('fronts', []),
                'shortlist': pid in shortlist, 'roles': shortlist.get(pid, []),
                'parent': c.get('parent'), 'seed': c['provenance'].get('seed'),
                'generator': c['provenance'].get('generator'), 'sha256': c['content_sha256'],
                'grids': grids, 'geometry': portfolio_geometry(grids, 50),
                'lab_geometry': c['geometry'],
                'exact': {'p_ge1': ex['p_at_least_one_gain']['decimal'],
                          'p_ge2': ex['p_at_least_two_gains']['decimal'],
                          'mean': ex['mean_winning_grids']['decimal'],
                          'mean_fraction': ex['mean_winning_grids']['fraction'],
                          'variance': ex['variance_winning_grids']['decimal'],
                          'dist': [x['probability']['decimal'] for x in ex['winning_grid_count_distribution']]}})
        gens.append({'game': 'euromillions', 'generation': 1, 'status': 'recherche en cours',
                     'label': 'Génération 1 — recherche HPC (Monte-Carlo) puis évaluation exacte',
                     'grids_per_portfolio': 30, 'stake_eur': 2.5, 'domain': 50,
                     'outcomes': sel['draw_space'], 'source': str(sel_path.relative_to(LAB)),
                     'source_sha256': sha256_file(sel_path), 'items': items})
    # Keno : références Phase 3A
    kdir = LAB / 'reports' / 'phase3a_portfolio_search' / 'portfolios'
    kitems = []
    for pid, fam in (('REF_RANDOM', 'RANDOM'), ('REF_BALANCED', 'BALANCED'), ('REF_POOL14', 'POOL14')):
        path = kdir / (pid + '.txt')
        if path.exists():
            grids = [[[int(x) for x in line.split()]] for line in path.read_text().splitlines() if line.strip()]
            kitems.append({'id': pid, 'family': fam, 'sha256': sha256_file(path), 'grids': grids,
                           'geometry': portfolio_geometry(grids, 56)})
    if kitems:
        gens.append({'game': 'keno', 'generation': 1, 'status': 'recherche en cours',
                     'label': 'Génération 1 — références Phase 3A (HPC)', 'grids_per_portfolio': 30,
                     'domain': 56, 'items': kitems})
    # Loto : catalogue durable
    lcat = LAB / 'portfolios' / 'loto' / 'catalog.jsonl'
    if lcat.exists():
        litems = []
        for line in lcat.read_text().splitlines():
            e = json.loads(line)
            path = LAB / e['source']['path']
            if path.exists():
                grids = read_grids(path)
                litems.append({'id': e['id'], 'family': e['family'], 'sha256': e['content_sha256'],
                               'grids': grids, 'geometry': portfolio_geometry(grids, 49),
                               'lab_geometry': e.get('geometry')})
        gens.append({'game': 'loto', 'generation': 1, 'status': 'recherche en cours',
                     'label': 'Génération 1 — catalogue de démonstration', 'domain': 49, 'items': litems})
    return gens


# ---------------------------------------------------------------- facts
def facts_for(draws, rows, laws, patterns, wanted):
    idx = build_indexes(laws)
    pascal = {t: Counter() for t in (2, 3, 4, 5)}
    out = {}
    for i, d in enumerate(draws):
        if d['id'] in wanted:
            out[d['id']] = build_draw_facts(d, rows[:i], laws, idx, patterns, pascal)
        for t in (2, 3, 4, 5):
            pascal[t].update(combinations(d['main'], t))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', type=int, default=12, help='nombre de derniers tirages avec facts')
    parser.add_argument('--draw', action='append', default=[], help='identifiant de tirage supplémentaire')
    args = parser.parse_args()
    started = time.time()
    laws_path = DATA / 'exact_laws.json'
    laws = read_json(laws_path)
    patterns = load_patterns()
    if laws['patterns_sha256'] != sha256_file(__import__('common').PATTERNS):
        raise SystemExit('patterns.py a changé : relancer engine/exact_laws.py avant build_data.py')
    draws, db_sha = load_draws()
    rows = history_rows(draws, patterns)
    write_json(DATA / 'draws.json', {
        'schema': 'aleaquant-draws-v1', 'game_id': 'euromillions', 'main_fields': MAIN_FIELDS + MAIN_CAT,
        'star_fields': STAR_FIELDS, 'current_rule': CURRENT_RULE,
        'rows': [[d['id'], d['date'], d['rule'], list(d['main']), list(d['stars']),
                  [r['main'][f] for f in MAIN_FIELDS + MAIN_CAT],
                  [r['stars'][f] for f in STAR_FIELDS] if r['stars'] else None]
                 for d, r in zip(draws, rows)]})
    write_json(DATA / 'laws.json', build_laws(laws, draws, rows))
    rng = np.random.default_rng(SEED)
    write_json(DATA / 'atlas.json', {'schema': 'aleaquant-atlas-v1', 'engine': ENGINE_VERSION,
                                      'cooccurrence': cooccurrences(draws, rng), 'portfolios': portfolios()})
    wanted = {d['id'] for d in draws[-args.facts:]} | set(args.draw)
    facts = facts_for(draws, rows, laws, patterns, wanted)
    for draw_id, f in facts.items():
        write_json(DATA / 'facts' / (draw_id + '.json'), f, compact=False)
    latest = draws[-1]['id']
    write_json(DATA / 'facts' / 'latest.json', facts[latest], compact=False)
    manifest = {'schema': 'aleaquant-data-manifest-v1', 'engine': ENGINE_VERSION,
                'built_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                'history_db': str(HISTORY_DB.name), 'history_db_sha256': db_sha,
                'draws': len(draws), 'first': draws[0]['date'], 'last': draws[-1]['date'],
                'latest_draw': latest, 'facts': sorted(facts),
                'exact_laws_patterns_sha256': laws['patterns_sha256'],
                'seconds': round(time.time() - started, 1)}
    write_json(DATA / 'manifest.json', manifest, compact=False)
    print(json.dumps(manifest, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
