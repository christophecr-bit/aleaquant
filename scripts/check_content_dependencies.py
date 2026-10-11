"""Gate documentary prerequisites before the standard Wrangler production build.

Version 1.0 · 2026-10-10. Read-only checks by default. The observe subcommand
only fetches an anonymous public response; it never deploys or creates articles.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from content_dependencies import (DependencyError, DEFAULT_REGISTRY, attach_publications,
                                  deployment_report, digest, load_registry, plan_batch,
                                  publication_report, verify_live_prerequisites)


def observe(registry, target_path, deployment_id, evidence_dir, base_dir=ROOT, references=None):
    """Record an actual anonymous HTTP body after a separately approved deployment."""
    nodes = [node for node in registry['nodes'] if node['target']['path'] == target_path]
    if references is not None:
        selected = {(reference['id'], reference['version']) for reference in references}
        nodes = [node for node in nodes if (node['id'], node['version']) in selected]
        if {(node['id'], node['version']) for node in nodes} != selected:
            raise DependencyError('Version de notion absente de cette cible')
    elif len({node['id'] for node in nodes}) != len(nodes):
        raise DependencyError('Plusieurs versions conservées : déclarer chaque --notion id@version à observer')
    if not nodes or any(node['kind'] != 'notion' for node in nodes):
        raise DependencyError('Observation directe réservée aux cibles de notions déclarées')
    base = Path(base_dir).resolve()
    directory = Path(evidence_dir).resolve()
    if base not in directory.parents:
        raise DependencyError('Répertoire de preuve doit être dans le dépôt')
    url = registry['production_origin'] + '/' + target_path
    if url.endswith('/index.html'):
        url = url.removesuffix('index.html')
    request = Request(url, headers={'Accept-Encoding': 'identity', 'User-Agent': 'AleaQuant-documentary-proof/1.0'})
    with urlopen(request, timeout=20) as response:
        status, final_url = response.status, response.geturl()
        # A login redirect, a protected staging response or another host cannot pass.
        if status != 200 or final_url != url:
            raise DependencyError('La cible ne répond pas HTTP 200 publiquement à son URL exacte')
        body = response.read(5_000_001)
    if len(body) > 5_000_000:
        raise DependencyError('Réponse de preuve dépasse la borne de 5 Mo')
    asset_sha = sha256(body).hexdigest()
    response_path = directory / f'{asset_sha}.html'
    directory.mkdir(parents=True, exist_ok=True)
    if response_path.exists() and response_path.read_bytes() != body:
        raise DependencyError('Preuve immuable déjà présente avec un autre contenu')
    response_path.write_bytes(body)
    observation = {'environment': 'production', 'anonymous': True, 'url': final_url,
                   'http_status': status, 'checked_at': datetime.now(timezone.utc).isoformat(),
                   'deployment_id': deployment_id, 'asset_sha256': asset_sha,
                   'response_path': response_path.relative_to(base).as_posix()}
    observation['id'] = digest(observation)
    result = attach_publications(registry, observation,
                                 [{'id': node['id'], 'version': node['version']} for node in nodes], base)
    return result, observation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument('--base-dir', type=Path, default=ROOT)
    parser.add_argument('--assets', type=Path, default=ROOT / 'dist')
    parser.add_argument('--live', action='store_true', help='Reconfirmer les prérequis par GET public anonyme')
    parser.add_argument('--live-on-deploy', action='store_true', help='GET uniquement quand WRANGLER_COMMAND=deploy')
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('validate')
    check = commands.add_parser('check')
    check.add_argument('subject')
    check.add_argument('--version', required=True)
    check.add_argument('--sha256')
    plan = commands.add_parser('plan')
    plan.add_argument('subjects', nargs='+', help='id@version')
    observation = commands.add_parser('observe')
    observation.add_argument('--target-path', required=True)
    observation.add_argument('--deployment-id', required=True)
    observation.add_argument('--notion', action='append', help='id@version ; répéter pour les versions effectivement présentes')
    observation.add_argument('--evidence-dir', type=Path, default=ROOT / 'docs/deployments/content-dependencies')
    args = parser.parse_args(argv)
    try:
        registry = load_registry(args.registry)
        if args.command == 'validate':
            result = {'status': 'valid', 'nodes': len(registry['nodes'])}
        elif args.command == 'check':
            result = publication_report(registry, args.subject, args.version, args.sha256, args.base_dir)
        elif args.command == 'plan':
            subjects = []
            for value in args.subjects:
                node_id, version = value.rsplit('@', 1)
                subjects.append({'id': node_id, 'version': version})
            result = plan_batch(registry, subjects)
        elif args.command == 'observe':
            references = None
            if args.notion:
                references = []
                for value in args.notion:
                    node_id, version = value.rsplit('@', 1)
                    references.append({'id': node_id, 'version': version})
            updated, observation = observe(registry, args.target_path, args.deployment_id,
                                           args.evidence_dir, args.base_dir, references)
            temporary = args.registry.with_suffix('.tmp')
            temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temporary.replace(args.registry)
            result = {'status': 'observed_publicly', 'observation': observation}
        else:
            result = deployment_report(registry, args.assets, args.base_dir)
            if result['status'] == 'ready' and (args.live or (
                    args.live_on_deploy and os.environ.get('WRANGLER_COMMAND') == 'deploy')):
                result['live_verification'] = verify_live_prerequisites(registry, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('status') == 'blocked' else 0
    except (DependencyError, OSError, ValueError, HTTPError, URLError) as error:
        print(f'Publication refusée : {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
