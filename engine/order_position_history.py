"""Covariance observée des positions ordonnées, par jeu et règle historique.

AleaQuant · 30/09/2026 · v0.1 (étude locale, aucun effet sur le site).
Source : aleaquant-data/data/aleaquant.sqlite3, dernières révisions immuables.
Historique : estime séparément les régimes et relie les moments observés à span.
TODO : choisir les fenêtres d'audit à l'avance et calibrer les tests statistiques.
"""
import argparse
from collections import defaultdict
from datetime import date as calendar_date
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from order_position_covariance import report as theoretical_report

DEFAULT_STORE = Path(__file__).resolve().parents[2] / 'aleaquant-data/data/aleaquant.sqlite3'


def rule_main_regime(rule):
    """Lit les deux formats historiques de règles présents dans la base source."""
    if 'picks' in rule and 'domains' in rule:
        return int(rule['picks']['main']), int(rule['domains']['main'])
    game = rule['game']
    main_draw = next(item for item in game['draw'] if item['component'] == 'main')
    main_component = next(item for item in game['components'] if item['name'] == 'main')
    if main_component['low'] != 1 or main_component['replacement']:
        raise ValueError('Règle non compatible avec un tirage uniforme sans remise')
    return int(main_draw['count']), int(main_component['high'])


def sample_moments(draws):
    """Moyenne et covariance empirique non biaisée (diviseur m-1), exactes."""
    if not draws:
        raise ValueError('Échantillon vide')
    m, k = len(draws), len(draws[0])
    if any(len(row) != k for row in draws):
        raise ValueError('Taille des tirages incohérente')
    sums = [sum(row[i] for row in draws) for i in range(k)]
    means = tuple(Fraction(value, m) for value in sums)
    if m < 2:
        return means, None
    products = [[0] * k for _ in range(k)]
    for row in draws:
        for i in range(k):
            for j in range(i, k):
                products[i][j] += row[i] * row[j]
    covariance = [[Fraction(0) for _ in range(k)] for _ in range(k)]
    for i in range(k):
        for j in range(i, k):
            value = (Fraction(products[i][j]) - m * means[i] * means[j]) / (m - 1)
            covariance[i][j] = covariance[j][i] = value
    return means, tuple(tuple(row) for row in covariance)


def _latest_draws(conn):
    return conn.execute('''SELECT r.game, r.draw_id, r.body, r.sha FROM revisions r
        WHERE r.revision=(SELECT MAX(r2.revision) FROM revisions r2
                          WHERE r2.game=r.game AND r2.draw_id=r.draw_id)''')


def historical_report(store=DEFAULT_STORE, *, start_date=None, end_date=None):
    """Rapport rétrospectif, sans p-value, sur les tirages de la fenêtre demandée."""
    store = Path(store)
    if not store.is_file():
        raise FileNotFoundError(store)
    for cutoff in (start_date, end_date):
        if cutoff is not None:
            if calendar_date.fromisoformat(cutoff).isoformat() != cutoff:
                raise ValueError('Date attendue au format YYYY-MM-DD')
    if start_date and end_date and start_date > end_date:
        raise ValueError('La date de début dépasse la date de fin')
    conn = sqlite3.connect(f'file:{store}?mode=ro', uri=True)
    try:
        rules = {rule_id: json.loads(body) for rule_id, body in
                 conn.execute('SELECT id, body FROM rules')}
        groups = defaultdict(list)
        validated_regimes = set()
        for game_id, draw_id, body, revision_sha in _latest_draws(conn):
            row = json.loads(body)
            if row['game_id'] != game_id or row['draw_id'] != draw_id:
                raise ValueError(f'Identité du tirage incohérente : {draw_id}')
            date = row['occurred_on']
            calendar_date.fromisoformat(date)
            if (start_date and date < start_date) or (end_date and date > end_date):
                continue
            rule_id = row['rule_id']
            rule = rules[rule_id]
            if rule.get('game_id', rule.get('game', {}).get('game_id')) != game_id:
                raise ValueError(f'Règle d’un autre jeu : {rule_id}')
            picks, domain = rule_main_regime(rule)
            main = tuple(sorted(dict(row['values'])['main']))
            if (len(main) != picks or len(set(main)) != picks
                    or any(not isinstance(x, int) or not 1 <= x <= domain for x in main)):
                raise ValueError(f'Numéros principaux invalides : {draw_id}')
            regime = (game_id, picks, domain)
            if regime not in validated_regimes:
                theoretical_report(game_id, picks, domain)  # refuse un couple inconnu
                validated_regimes.add(regime)
            groups[(game_id, rule_id, picks, domain)].append(
                (date, str(row.get('session') or ''), draw_id, revision_sha, main))
    finally:
        conn.close()

    results = []
    for (game_id, rule_id, picks, domain), records in sorted(groups.items()):
        records.sort(key=lambda item: (item[0], item[1], item[2]))
        draws = [record[4] for record in records]
        mean, covariance = sample_moments(draws)
        theory = theoretical_report(game_id, picks, domain)
        identity = '\n'.join(f'{draw_id}:{revision_sha}' for _, _, draw_id, revision_sha, _ in records)
        spans = [row[-1] - row[0] for row in draws]
        span_mean = Fraction(sum(spans), len(spans))
        span_variance = (sum((value - span_mean) ** 2 for value in spans) / (len(spans) - 1)
                         if len(spans) > 1 else None)
        if covariance is not None:
            from_matrix = covariance[-1][-1] + covariance[0][0] - 2 * covariance[0][-1]
            if from_matrix != span_variance:
                raise AssertionError('Identité de variance de span rompue')
        results.append({
            'game_id': game_id, 'component': 'main', 'rule_id': rule_id,
            'picks': picks, 'domain': domain, 'draw_count': len(records),
            'first_date': records[0][0], 'last_date': records[-1][0],
            'revisions_sha256': sha256(identity.encode()).hexdigest(),
            'estimator': 'sample covariance, denominator m-1',
            'mean': [str(value) for value in mean],
            'covariance': ([[str(value) for value in row] for row in covariance]
                           if covariance is not None else None),
            'span_mean': str(span_mean),
            'span_variance': str(span_variance) if span_variance is not None else None,
            'theory': theory,
        })
    return {'schema': 'aleaquant-order-position-history-v1',
            'source': 'aleaquant-data SQLite revisions (read-only)',
            'window': {'start_date': start_date, 'end_date': end_date,
                       'basis': 'draw date, retrospective latest revisions'},
            'statistical_test': None,
            'groups': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, default=DEFAULT_STORE)
    parser.add_argument('--start-date', default=None)
    parser.add_argument('--end-date', default=None)
    args = parser.parse_args()
    print(json.dumps(historical_report(args.store, start_date=args.start_date,
                                       end_date=args.end_date), ensure_ascii=False, indent=2))
