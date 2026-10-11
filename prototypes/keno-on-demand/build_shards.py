"""Prototype isolated from the published AleaQuant build."""
import gzip
import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

SOURCE = Path(os.environ.get(
    'ALEAQUANT_DATA_DB',
    Path(__file__).resolve().parents[3] / 'aleaquant-data/data/aleaquant.sqlite3'))
OUT = Path(__file__).resolve().parent / 'assets'


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f'file:{SOURCE}?mode=ro', uri=True)
    rows = con.execute('''SELECT r.body FROM revisions r WHERE r.game='keno'
        AND r.revision=(SELECT MAX(r2.revision) FROM revisions r2
                        WHERE r2.game=r.game AND r2.draw_id=r.draw_id)''')
    by_month = defaultdict(list)
    for (body,) in rows:
        record = json.loads(body)
        by_month[record['occurred_on'][:7]].append({
            'id': record['draw_id'], 'date': record['occurred_on'],
            'session': record.get('session'), 'rule': record['rule_id'],
            'main': dict(record['values'])['main'],
        })
    manifest = {'schema': 'aleaquant-keno-index-v0', 'id_to_month': {}, 'months': {}}
    measurements = []
    for month, draws in sorted(by_month.items()):
        draws.sort(key=lambda d: (d['date'], d['session'] or '', d['id']))
        for d in draws:
            if d['id'] in manifest['id_to_month']:
                raise ValueError(f'duplicate draw_id: {d["id"]}')
            manifest['id_to_month'][d['id']] = month
        manifest['months'][month] = {'count': len(draws), 'first': draws[0]['id'],
                                     'last': draws[-1]['id']}
        payload = {'schema': 'aleaquant-keno-month-v0', 'game_id': 'keno',
                   'month': month, 'draws': draws}
        path = OUT / f'keno-{month}.json'
        raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
        path.write_bytes(raw)
        measurements.append({'month': month, 'draws': len(draws),
                             'bytes': len(raw), 'gzip_bytes': len(gzip.compress(raw, mtime=0))})
    raw_manifest = json.dumps(manifest, ensure_ascii=False, separators=(',', ':')).encode()
    (OUT / 'index.json').write_bytes(raw_manifest)
    result = {'total_draws': len(manifest['id_to_month']), 'months': len(by_month),
              'index_bytes': len(raw_manifest),
              'index_gzip_bytes': len(gzip.compress(raw_manifest, mtime=0)),
              'monthly': measurements}
    (Path(__file__).resolve().parent / 'measurements.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'monthly'}, indent=2))


if __name__ == '__main__':
    build()
