"""Profil de rareté de chaque mesure sur tout l'historique.

Pourquoi : un badge de rareté n'informe que si la mesure peut AUSSI ne pas être rare.
`main.sorted_gaps` est TRÈS RARE pour les 1984 tirages — son badge ne distingue donc
rien. `main.sum` n'est jamais COURANTE : « peu courante » y est la normale, pas une
information. D'où la notion de NIVEAU DE RÉFÉRENCE (le niveau le plus fréquent de la
mesure) : une mesure n'est notable que si son niveau dépasse sa propre référence.

    python3 engine/rarity_profiles.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, ENGINE_VERSION, write_json  # noqa: E402

ORDER = {'COMMON': 0, 'UNCOMMON': 1, 'RARE': 2, 'VERY_RARE': 3}


def build():
    levels = defaultdict(Counter)
    for fp in sorted((DATA / 'facts').glob('EM-*.json')):
        for f in json.loads(fp.read_text(encoding='utf-8'))['facts']:
            if 'rarity' in f and f.get('metric'):
                levels[f['metric']][f['rarity']] += 1

    metrics = {}
    for metric, counts in sorted(levels.items()):
        n = sum(counts.values())
        baseline, base_n = max(counts.items(), key=lambda kv: (kv[1], -ORDER[kv[0]]))
        constant = len(counts) == 1
        metrics[metric] = {
            'draws': n,
            'levels': {k: counts[k] for k in ORDER if k in counts},
            # niveau le plus fréquent : en dessous ou à ce niveau, la mesure est dans sa
            # normale et NE DOIT PAS être qualifiée de rare ou de notable.
            'baseline': baseline,
            'baseline_share': round(base_n / n, 4),
            'constant': constant,
            # un badge n'a de sens que s'il existe des tirages au-dessus de la référence
            'informative': not constant and any(
                ORDER[k] > ORDER[baseline] for k in counts),
            'share_above_baseline': round(
                sum(c for k, c in counts.items() if ORDER[k] > ORDER[baseline]) / n, 4),
        }

    out = {
        'schema': 'aleaquant-rarity-profiles-v1', 'engine': ENGINE_VERSION,
        'method': ("part des tirages de l'historique complet dans chaque niveau de "
                   "rareté, par mesure ; baseline = niveau le plus fréquent"),
        'draws': max(m['draws'] for m in metrics.values()),
        'metrics': metrics,
    }
    write_json(DATA / 'rarity_profiles.json', out, compact=False)
    return out


if __name__ == '__main__':
    r = build()
    nb_const = sum(1 for m in r['metrics'].values() if m['constant'])
    nb_info = sum(1 for m in r['metrics'].values() if m['informative'])
    print(f"{len(r['metrics'])} mesures profilées sur {r['draws']} tirages")
    print(f"  {nb_const} à rareté constante (badge inutile)")
    print(f"  {nb_info} informatives (des tirages dépassent leur niveau de référence)")
    for metric, m in sorted(r['metrics'].items(), key=lambda kv: kv[1]['share_above_baseline']):
        flag = 'CONSTANTE' if m['constant'] else f"{100*m['share_above_baseline']:5.1f} % au-dessus"
        print(f"  {metric:38} réf.={m['baseline']:10} {flag}")
