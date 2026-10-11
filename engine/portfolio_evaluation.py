"""Évaluation Monte-Carlo bornée et reprenable de grilles EuroMillions gelées.

Les tirages sont uniformes sans remise et communs à tous les portefeuilles.
Le checkpoint contient la frontière durable et l'état du générateur, sans
qualifier une évaluation interrompue de résultat final.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
import time

import numpy as np

from portfolio_import import content_hash

ENGINE_VERSION = 'aleaquant-portfolio-monte-carlo-v1'
CHECKPOINT_SCHEMA = 'aleaquant-portfolio-evaluation-checkpoint-v1'
EVENTS = ('any_prize', 'multiple_prizes', 'at_least_3_numbers', 'at_least_4_numbers')
COUNTERS = EVENTS + ('winning_grids_sum',)
TOTAL = math.comb(50, 5) * math.comb(12, 2)
MAX_BATCH_WORK = 2_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _integer(value, minimum, maximum, name):
    require(type(value) is int and minimum <= value <= maximum, f'{name} : entier invalide')


def _values(values, count, maximum, name):
    require(isinstance(values, (list, tuple)) and len(values) == count, f'{name} : cardinalité invalide')
    require(all(type(value) is int and 1 <= value <= maximum for value in values),
            f'{name} : domaine invalide')
    require(len(set(values)) == count, f'{name} : valeurs répétées')
    return sorted(values)


def _grid_rows(grids, name='grilles', allow_duplicates=False, allow_empty=False):
    require(isinstance(grids, (list, tuple)) and (allow_empty or len(grids) > 0),
            f'{name} : liste invalide')
    require(len(grids) <= (10000 if allow_duplicates else 2000), f'{name} : effectif trop grand')
    rows = []
    for index, grid in enumerate(grids):
        require(isinstance(grid, (list, tuple)) and len(grid) == 2, f'{name}[{index}] : format invalide')
        rows.append([_values(grid[0], 5, 50, f'{name}[{index}] numéros'),
                     _values(grid[1], 2, 12, f'{name}[{index}] étoiles')])
    if not allow_duplicates:
        require(len({(tuple(g[0]), tuple(g[1])) for g in rows}) == len(rows),
                f'{name} : grilles répétées')
    return rows


def exact_analytics(grids):
    """Espérance exacte du nombre de grilles gagnantes et probabilité 5+2."""
    count = len(_grid_rows(grids))
    denominator = math.comb(50, 5)
    one = sum(math.comb(5, hits) * math.comb(45, 5 - hits) / denominator
              for hits in range(2, 6))
    one += 5 * math.comb(45, 4) / TOTAL
    return {'jackpot_probability': count / TOTAL,
            'theoretical_mean_winning_grids': count * one}


def _count_arrays(grids, numbers, stars):
    size = len(numbers)
    if size == 0:
        return {name: 0 for name in COUNTERS}
    ni = np.zeros((size, 51), dtype=np.bool_)
    si = np.zeros((size, 13), dtype=np.bool_)
    ni[np.arange(size)[:, None], numbers] = True
    si[np.arange(size)[:, None], stars] = True
    gn = np.array([g[0] for g in grids], dtype=np.int16)
    gs = np.array([g[1] for g in grids], dtype=np.int16)
    nh = ni[:, gn].sum(axis=2, dtype=np.int16)
    sh = si[:, gs].sum(axis=2, dtype=np.int16)
    winning = ((nh >= 2) | ((nh == 1) & (sh == 2))).sum(axis=1, dtype=np.int16)
    best_numbers = nh.max(axis=1)
    return {'any_prize': int(np.count_nonzero(winning >= 1)),
            'multiple_prizes': int(np.count_nonzero(winning >= 2)),
            'at_least_3_numbers': int(np.count_nonzero(best_numbers >= 3)),
            'at_least_4_numbers': int(np.count_nonzero(best_numbers >= 4)),
            'winning_grids_sum': int(winning.sum(dtype=np.int64))}


def evaluate_draws(grids, draws):
    """Compter les événements sur des tirages explicites, sans générateur RNG."""
    grids = _grid_rows(grids)
    draws = _grid_rows(draws, 'tirages', allow_duplicates=True, allow_empty=True)
    require(len(grids) * len(draws) <= MAX_BATCH_WORK, 'plafond de travail dépassé')
    numbers = np.array([d[0] for d in draws], dtype=np.int16)
    stars = np.array([d[1] for d in draws], dtype=np.int16)
    return _count_arrays(grids, numbers, stars)


def _protocol(protocol):
    require(isinstance(protocol, dict), 'protocole invalide')
    required = {'method', 'draws', 'seed', 'batch_size', 'max_seconds', 'metrics'}
    require(set(protocol) == required, 'champs protocole inconnus ou manquants')
    require(protocol['method'] == 'monte_carlo', 'méthode de simulation inconnue')
    _integer(protocol['draws'], 1, 1_000_000, 'draws')
    _integer(protocol['seed'], 0, 2 ** 63 - 1, 'seed')
    _integer(protocol['batch_size'], 1, 10000, 'batch_size')
    require(_finite(protocol['max_seconds']) and 0 < protocol['max_seconds'] <= 3600,
            'max_seconds : durée invalide')
    require(isinstance(protocol['metrics'], list) and len(protocol['metrics']) == len(EVENTS)
            and all(isinstance(x, str) for x in protocol['metrics'])
            and set(protocol['metrics']) == set(EVENTS), 'métriques inconnues ou répétées')
    # Copy caller-owned lists before creating the persistent signature.
    return json.loads(json.dumps(protocol))


def _portfolios(portfolios):
    require(isinstance(portfolios, list) and 1 <= len(portfolios) <= 100, 'portefeuilles invalides')
    prepared = {}
    for item in portfolios:
        require(isinstance(item, dict) and {'content_sha256', 'grids'} <= item.keys(),
                'portefeuille incomplet')
        grids = sorted(_grid_rows(item['grids']))
        fingerprint = item['content_sha256']
        require(isinstance(fingerprint, str) and re.fullmatch('[0-9a-f]{64}', fingerprint) is not None,
                'empreinte portefeuille invalide')
        require(fingerprint == content_hash(grids), 'empreinte différente des grilles')
        require(fingerprint not in prepared, 'portefeuille répété')
        prepared[fingerprint] = grids
    return dict(sorted(prepared.items()))


def _environment():
    return {'python': platform.python_version(), 'numpy': np.__version__,
            'rng': 'PCG64', 'machine': platform.machine(), 'byteorder': sys.byteorder}


def _source_hash():
    """Refuse une reprise après un changement du moteur, même sans bump de version."""
    return sha256(Path(__file__).read_bytes()).hexdigest()


def _uniform_draws(rng, count):
    # Independent uniform permutations give exactly five distinct numbers
    # and two distinct stars; the two game domains are shuffled separately.
    numbers = rng.permuted(np.tile(np.arange(1, 51, dtype=np.int16), (count, 1)), axis=1)[:, :5]
    stars = rng.permuted(np.tile(np.arange(1, 13, dtype=np.int16), (count, 1)), axis=1)[:, :2]
    return numbers, stars


def _atomic_json(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


@contextmanager
def _evaluation_lock(directory):
    with (directory / '.evaluation.lock').open('a+') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('évaluation déjà active dans ce dossier') from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _checkpoint_write(path, payload):
    _atomic_json(path, {'payload': payload, 'checksum_sha256': _digest(payload)})


def _checkpoint_read(path, metadata, prepared):
    require(path.stat().st_size <= 2_000_000, 'checkpoint trop volumineux')
    def unique_pairs(items):
        result = {}
        for name, value in items:
            require(name not in result, 'clé checkpoint répétée')
            result[name] = value
        return result
    try:
        raw = json.loads(path.read_text(encoding='utf-8'),
                         object_pairs_hook=unique_pairs,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError('checkpoint non fini')))
        require(isinstance(raw, dict) and set(raw) == {'payload', 'checksum_sha256'}, 'format checkpoint invalide')
        payload = raw['payload']
        require(isinstance(payload, dict) and set(payload) == set(metadata) | {
            'status', 'completed_draws', 'batch_count', 'counts', 'rng_state', 'draw_stream_sha256'},
                'champs checkpoint invalides')
        require(raw['checksum_sha256'] == _digest(payload), 'checksum checkpoint incompatible')
        _protocol(payload['protocol'])
        require(all(payload[name] == value for name, value in metadata.items()),
                'checkpoint provenant d’un autre protocole, environnement ou ensemble')
        completed, batch_count = payload['completed_draws'], payload['batch_count']
        draws, batch = metadata['protocol']['draws'], metadata['protocol']['batch_size']
        _integer(completed, 0, draws, 'frontière checkpoint')
        _integer(batch_count, 0, (draws + batch - 1) // batch, 'batch_count checkpoint')
        require(completed == draws or completed % batch == 0, 'frontière checkpoint non alignée')
        require(batch_count == (completed + batch - 1) // batch, 'batches checkpoint incompatibles')
        require(payload['status'] == ('complete' if completed == draws else 'interrupted'), 'état checkpoint incompatible')
        require(isinstance(payload['draw_stream_sha256'], str)
                and re.fullmatch('[0-9a-f]{64}', payload['draw_stream_sha256']) is not None,
                'empreinte des tirages invalide')
        require(isinstance(payload['counts'], dict) and set(payload['counts']) == set(prepared),
                'ensemble de compteurs différent')
        for fingerprint, grids in prepared.items():
            counts = payload['counts'][fingerprint]
            require(isinstance(counts, dict) and set(counts) == set(COUNTERS), 'compteurs inconnus/manquants')
            for name in EVENTS:
                _integer(counts[name], 0, completed, 'compteur ' + name)
            _integer(counts['winning_grids_sum'], 0, completed * len(grids), 'compteur des gagnantes')
            require(counts['multiple_prizes'] <= counts['any_prize']
                    and counts['at_least_4_numbers'] <= counts['at_least_3_numbers'] <= counts['any_prize'],
                    'événements checkpoint incohérents')
            require(counts['any_prize'] + counts['multiple_prizes'] <= counts['winning_grids_sum']
                    <= counts['any_prize'] + (len(grids) - 1) * counts['multiple_prizes'],
                    'moyenne checkpoint incohérente')
        state = payload['rng_state']
        require(isinstance(state, dict) and set(state) == {'bit_generator', 'state', 'has_uint32', 'uinteger'}
                and state['bit_generator'] == 'PCG64', 'générateur checkpoint incompatible')
        require(isinstance(state['state'], dict) and set(state['state']) == {'state', 'inc'}, 'état RNG invalide')
        for name in ('state', 'inc'):
            _integer(state['state'][name], 0, 2 ** 128 - 1, 'état RNG ' + name)
        require(state['state']['inc'] % 2 == 1, 'incrément RNG invalide')
        _integer(state['has_uint32'], 0, 1, 'has_uint32')
        _integer(state['uinteger'], 0, 2 ** 32 - 1, 'uinteger')
        return payload
    except (KeyError, TypeError, json.JSONDecodeError, OverflowError) as exc:
        raise ValueError('checkpoint corrompu') from exc


def _wilson(count, draws):
    z = 1.95996398454
    probability = count / draws
    denominator = 1 + z * z / draws
    middle = (probability + z * z / (2 * draws)) / denominator
    half = z * math.sqrt(probability * (1 - probability) / draws
                         + z * z / (4 * draws * draws)) / denominator
    return [max(0.0, middle - half), min(1.0, middle + half)]


def _result(payload, prepared):
    complete = payload['status'] == 'complete'
    results = {}
    if complete:
        draws, protocol = payload['completed_draws'], payload['protocol']
        protocol_hash = _digest(protocol)
        for fingerprint, grids in prepared.items():
            counts = payload['counts'][fingerprint]
            results[fingerprint] = {
                'draws': draws, 'seed': protocol['seed'], 'independent_of_generation': True,
                'same_draws_for_all': True, 'content_sha256': fingerprint,
                'engine_version': ENGINE_VERSION, 'environment': payload['environment'],
                'source_sha256': payload['source_sha256'],
                'protocol_sha256': protocol_hash, 'draw_stream_sha256': payload['draw_stream_sha256'],
                'evaluation_sha256': _digest({'content_sha256': fingerprint,
                                             'signature': payload['signature'],
                                             'draw_stream_sha256': payload['draw_stream_sha256']}),
                'metrics': {name: {'count': counts[name], 'probability': counts[name] / draws,
                                   'ci95_wilson': _wilson(counts[name], draws)} for name in EVENTS},
                'mean_winning_grids': counts['winning_grids_sum'] / draws,
                **exact_analytics(grids),
            }
    return {'status': payload['status'], 'completed_draws': payload['completed_draws'],
            'batch_count': payload['batch_count'], 'results': results,
            'protocol': payload['protocol'], 'engine_version': ENGINE_VERSION,
            'source_sha256': payload['source_sha256'],
            'environment': payload['environment'], 'signature': payload['signature'],
            'draw_stream_sha256': payload['draw_stream_sha256']}


def evaluate_many(portfolios, protocol, output_dir, progress=None, stop_after_batches=None):
    """Évaluer ou reprendre ; interrompu => aucun résultat final dans results.

    max_seconds borne chaque appel aux frontières des batches. Un batch déjà
    commencé est terminé puis persisté atomiquement. Le générateur et les
    compteurs sont restaurés ensemble avant toute reprise.
    """
    protocol, prepared = _protocol(protocol), _portfolios(portfolios)
    require(protocol['batch_size'] * sum(len(g) for g in prepared.values()) <= MAX_BATCH_WORK,
            'batch_size dépasse le plafond de travail')
    require(progress is None or callable(progress), 'callback progress invalide')
    if stop_after_batches is not None:
        _integer(stop_after_batches, 0, 1_000_000, 'stop_after_batches')
    environment = _environment()
    metadata = {'schema': CHECKPOINT_SCHEMA, 'engine_version': ENGINE_VERSION,
                'source_sha256': _source_hash(),
                'environment': environment, 'protocol': protocol,
                'portfolio_hashes': list(prepared)}
    metadata['signature'] = _digest(metadata)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint, result_path = directory / 'checkpoint.json', directory / 'results.json'
    with _evaluation_lock(directory):
        rng = np.random.Generator(np.random.PCG64(protocol['seed']))
        if checkpoint.exists():
            payload = _checkpoint_read(checkpoint, metadata, prepared)
            try:
                rng.bit_generator.state = payload['rng_state']
            except (ValueError, TypeError, OverflowError) as exc:
                raise ValueError('état RNG checkpoint corrompu') from exc
        else:
            require(not result_path.exists(), 'résultats présents sans checkpoint ; dossier incompatible')
            payload = {**metadata, 'status': 'interrupted', 'completed_draws': 0, 'batch_count': 0,
                       'counts': {key: {name: 0 for name in COUNTERS} for key in prepared},
                       'rng_state': rng.bit_generator.state,
                       'draw_stream_sha256': sha256(b'aleaquant-common-draw-stream-v1').hexdigest()}
            _checkpoint_write(checkpoint, payload)
        start, call_batches = time.monotonic(), 0
        while payload['completed_draws'] < protocol['draws']:
            if time.monotonic() - start >= protocol['max_seconds']:
                break
            if stop_after_batches is not None and call_batches >= stop_after_batches:
                break
            count = min(protocol['batch_size'], protocol['draws'] - payload['completed_draws'])
            numbers, stars = _uniform_draws(rng, count)
            for fingerprint, grids in prepared.items():
                addition = _count_arrays(grids, numbers, stars)
                for name, value in addition.items():
                    payload['counts'][fingerprint][name] += value
            stream = sha256(bytes.fromhex(payload['draw_stream_sha256']))
            stream.update(numbers.astype('<i2', copy=False).tobytes(order='C'))
            stream.update(stars.astype('<i2', copy=False).tobytes(order='C'))
            payload['draw_stream_sha256'] = stream.hexdigest()
            payload['completed_draws'] += count
            payload['batch_count'] += 1
            payload['rng_state'] = rng.bit_generator.state
            payload['status'] = 'complete' if payload['completed_draws'] == protocol['draws'] else 'interrupted'
            _checkpoint_write(checkpoint, payload)
            call_batches += 1
            if progress is not None:
                progress({'status': 'complete' if payload['status'] == 'complete' else 'running',
                          'completed_draws': payload['completed_draws'],
                          'total_draws': protocol['draws'], 'batch_count': payload['batch_count']})
        result = _result(payload, prepared)
        result['checkpoint_path'] = str(checkpoint.resolve())
        if result['status'] == 'complete':
            _atomic_json(result_path, result)
        return result
