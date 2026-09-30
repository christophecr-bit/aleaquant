"""Chemins, lecture des tirages et utilitaires partagés du moteur AleaQuant V0.

Le moteur lit le laboratoire en lecture seule. Chemin configurable par
ALEAQUANT_LAB (défaut : ../loto-keno-lab-generic à côté de ce dépôt).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from fractions import Fraction
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'dist' / 'data'
LAB = Path(os.environ.get('ALEAQUANT_LAB', ROOT.parent / 'loto-keno-lab-generic')).resolve()
HISTORY_DB = Path(os.environ.get('ALEAQUANT_HISTORY_DB', LAB / 'data' / 'history' / 'euromillions.sqlite3'))
PATTERNS = Path(os.environ.get('ALEAQUANT_PATTERNS', LAB / 'src' / 'lottery_games' / 'euromillions' / 'patterns.py'))

ENGINE_VERSION = 'aleaquant-engine-v0.1'
CURRENT_RULE = 'euromillions-50-12-v1'

# Les étoiles d'EuroMillions ont changé deux fois : 9 étoiles jusqu'au 06/05/2011,
# 11 du 10/05/2011 au 23/09/2016, 12 depuis le 27/09/2016. Le dénominateur de la
# combinaison complète doit suivre la règle EN VIGUEUR À LA DATE du tirage, jamais la
# règle courante — sinon un tirage de 2011 annonce 1 sur 139 838 160 au lieu de
# 1 sur 116 531 800.
RULE_RE = re.compile(r'^euromillions-(\d+)-(\d+)-v\d+$')


def rule_star_total(rule_id):
    """Nombre de couples d'étoiles possibles sous la règle du tirage."""
    m = RULE_RE.match(rule_id or '')
    if not m:
        raise ValueError('règle de tirage inconnue : %r' % (rule_id,))
    return comb(int(m.group(2)), 2)


def rule_domains(rule_id):
    """(nombre de numéros du domaine, nombre d'étoiles) de la règle du tirage."""
    m = RULE_RE.match(rule_id or '')
    if not m:
        raise ValueError('règle de tirage inconnue : %r' % (rule_id,))
    return int(m.group(1)), int(m.group(2))


def rule_main_total(rule_id):
    """Nombre de combinaisons de numéros principaux sous la règle du tirage."""
    m = RULE_RE.match(rule_id or '')
    if not m:
        raise ValueError('règle de tirage inconnue : %r' % (rule_id,))
    return comb(int(m.group(1)), 5)

MAIN_FIELDS = ['sum', 'span', 'min_gap', 'max_gap', 'mean_gap', 'longest_consecutive_run',
               'consecutive_pairs', 'runs_ge2', 'max_same_decade', 'occupied_decades',
               'odd_count', 'low_count', 'repeated_terminal_digits', 'terminal_pair_collisions',
               'is_arithmetic_progression', 'longest_arithmetic_progression',
               'arithmetic_triples', 'clusteredness_close_pairs_5']
MAIN_CAT = ['sorted_gaps', 'decade_counts']
STAR_FIELDS = ['gap', 'consecutive', 'odd_count', 'low_count', 'sum', 'terminal_coincidence']
# seuils identiques à patterns.DEFAULT_RARITY_THRESHOLDS
RARITY = [('COMMON', 0.1), ('UNCOMMON', 0.01), ('RARE', 0.001), ('VERY_RARE', 0.0)]


def load_patterns():
    """Importe patterns.py du laboratoire sans installer le paquet."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('aleaquant_patterns', PATTERNS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def num(value):
    """Valeur scalaire JSON d'une métrique (bool -> 0/1, fraction -> float)."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        return float(Fraction(value))
    return value


def key(value) -> str:
    """Clé texte stable d'une valeur de métrique (utilisée dans les lois)."""
    if isinstance(value, (tuple, list)):
        return '-'.join(map(str, value))
    return repr(num(value)) if not isinstance(value, str) else repr(float(Fraction(value)))


def rarity(p: float) -> str:
    for label, threshold in RARITY:
        if p >= threshold:
            return label
    return 'VERY_RARE'


def load_draws():
    """Dernière révision de chaque tirage, triée par date. Lecture seule."""
    con = sqlite3.connect(f'file:{HISTORY_DB}?mode=ro', uri=True)
    best = {}
    for _game, draw_id, revision, body, sha in con.execute(
            'select game, draw_id, revision, body, sha from revisions'):
        if draw_id not in best or revision > best[draw_id][0]:
            best[draw_id] = (revision, json.loads(body), sha)
    draws = []
    for draw_id, (revision, body, sha) in best.items():
        values = {k: tuple(sorted(v)) for k, v in body['values']}
        draws.append({'id': draw_id, 'date': body['occurred_on'], 'rule': body['rule_id'],
                      'main': values['main'], 'stars': values['stars'], 'revision': revision,
                      'sha256': sha, 'source': body['source'].get('source_id'),
                      'publisher': body['source'].get('publisher')})
    draws.sort(key=lambda d: (d['date'], d['id']))
    return draws, sha256_file(HISTORY_DB)


def write_json(path: Path, value, compact=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    if compact:
        tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')))
    else:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def read_json(path: Path):
    return json.loads(Path(path).read_text())


if __name__ == '__main__':
    print(LAB, HISTORY_DB.exists(), PATTERNS.exists(), file=sys.stderr)
