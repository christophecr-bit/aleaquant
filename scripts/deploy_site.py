"""Check the actual asset lot, then optionally invoke the existing Wrangler deploy.

Version 1.0 · 2026-10-10. Default: report only, no network or deployment.
An isolated glossary lot can bootstrap definitions without publishing consumers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from content_dependencies import DependencyError, DEFAULT_REGISTRY, deployment_report, load_registry


def _jsonc(text):
    """Remove comments outside strings; preserve HTTPS URLs and escaped quotes."""
    out, index, quoted, escaped = [], 0, False, False
    while index < len(text):
        char = text[index]
        if quoted:
            out.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
            index += 1
        elif char == '"':
            quoted = True
            out.append(char)
            index += 1
        elif text.startswith('//', index):
            end = text.find('\n', index)
            index = len(text) if end < 0 else end
        elif text.startswith('/*', index):
            end = text.find('*/', index + 2)
            if end < 0:
                raise DependencyError('Commentaire JSONC non terminé')
            index = end + 2
        else:
            out.append(char)
            index += 1
    return json.loads(''.join(out))


def checked_config(assets, registry_path=DEFAULT_REGISTRY, config_path=ROOT / 'wrangler.jsonc', base_dir=ROOT):
    """Both the wrapper and Wrangler's build check the same absolute asset path."""
    assets, registry_path = Path(assets).resolve(), Path(registry_path).resolve()
    if not assets.is_dir() or any(path.is_symlink() for path in assets.rglob('*')):
        raise DependencyError('Lot assets absent ou contenant un lien symbolique')
    report = deployment_report(load_registry(registry_path), assets, base_dir)
    if report['status'] != 'ready':
        raise DependencyError('Lot bloqué : ' + '; '.join(
            f"{subject['subject']} — {blocker['reason']}"
            for subject in report['subjects'] for blocker in subject.get('blockers', [])))
    config = _jsonc(Path(config_path).read_text())
    if config.get('name') != 'aleaquant':
        raise DependencyError('Ce wrapper est réservé au Worker de production aleaquant')
    config['assets']['directory'] = str(assets)
    config['build'] = {'command': shlex.join([sys.executable, str(ROOT / 'scripts/check_content_dependencies.py'),
                                            '--registry', str(registry_path), '--base-dir', str(Path(base_dir).resolve()),
                                            '--assets', str(assets), '--live-on-deploy'])}
    return config, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=ROOT / 'dist')
    parser.add_argument('--registry', type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument('--execute', action='store_true', help='Déployer effectivement ce lot contrôlé')
    args = parser.parse_args(argv)
    try:
        config, report = checked_config(args.assets, args.registry)
        if not args.execute:
            print(json.dumps({'status': 'ready_not_deployed', 'gate': report}, ensure_ascii=False, indent=2))
            return 0
        if not (args.assets / 'index.html').is_file():
            raise DependencyError('Lot incomplet sans index.html du site : un upload d’un sous-ensemble supprimerait les autres assets du Worker')
        # Temporary config preserves routes; it replaces only the asset path and
        # the guard command. No --no-bundle or unguarded passthrough is exposed.
        with tempfile.TemporaryDirectory(prefix='.documentary-deploy-', dir=ROOT) as directory:
            path = Path(directory) / 'wrangler.json'
            path.write_text(json.dumps(config, ensure_ascii=False, indent=2))
            subprocess.run(['npx', 'wrangler', 'deploy', '--config', str(path)], cwd=ROOT, check=True)
        print('Déploiement terminé ; enregistrer séparément la réponse publique observée.')
        return 0
    except (DependencyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Déploiement refusé : {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
