"""Figer les assets de recette sans reconstruire ni modifier dist/.

Auteur : AleaQuant · Date : 2026-10-03 · Version : 1.1.
Historique : 1.0 snapshot indépendant; 1.1 liens internes adaptés à la recette.
Le snapshot est créé une seule fois à sa destination. Aucun accès réseau,
aucun calcul scientifique et aucun déploiement ne sont exécutés.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ASSET_LIMIT = 20_000
CONTROL_FILES = {".assetsignore", "_headers", "_redirects"}
ROBOTS_HEADER = "  X-Robots-Tag: noindex, nofollow, noarchive\n"
INTERNAL_HOSTS = {"aleaquant.org", "aleaquant.aleaquant.workers.dev"}
ATTRIBUTE = re.compile(r'''\s+([^\s/=>]+)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)''')


def recette_links(data: bytes) -> bytes:
    """Adapter seulement les href de <a>, sans réécrire le document HTML."""
    text = data.decode("utf-8")
    offsets = [0]
    for match in re.finditer("\n", text):
        offsets.append(match.end())
    changes = []

    class Anchors(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag != "a":
                return
            raw = self.get_starttag_text()
            line, column = self.getpos()
            offset = offsets[line - 1] + column
            for match in ATTRIBUTE.finditer(raw):
                if match.group(1).lower() != "href":
                    continue
                value = match.group(2)
                quoted = value.startswith(('"', "'"))
                href = value[1:-1] if quoted else value
                try:
                    url = urlsplit(href)
                    internal = (url.scheme.lower() in ("http", "https", "")
                                and url.hostname in INTERNAL_HOSTS)
                except ValueError:
                    internal = False
                if not internal:
                    continue
                # Garder le query/fragment tels qu'écrits (notamment &amp;).
                relative = url.path or "/"
                if relative.startswith("//"):
                    relative = "/." + relative
                if url.query:
                    relative += "?" + url.query
                if url.fragment:
                    relative += "#" + url.fragment
                start = offset + match.start(2) + int(quoted)
                end = offset + match.end(2) - int(quoted)
                changes.append((start, end, relative))

        handle_startendtag = handle_starttag

    parser = Anchors(convert_charrefs=False)
    parser.feed(text)
    parser.close()
    for start, end, replacement in reversed(changes):
        text = text[:start] + replacement + text[end:]
    return text.encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_state(repo: Path) -> dict:
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], text=True).rstrip("\n")
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    return {"head": git("rev-parse", "HEAD"), "dirty": bool(status),
            "status_porcelain": status.splitlines()}


def source_files(source: Path) -> list[Path]:
    ignore = source / ".assetsignore"
    rules = [line.strip() for line in ignore.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    unsupported = [rule for rule in rules if rule != "data/facts/**"]
    if unsupported:
        raise ValueError(f"Règles .assetsignore non prises en charge : {unsupported}")
    if "data/facts/**" not in rules:
        raise ValueError("Exclusion obligatoire data/facts/** absente de .assetsignore")
    files = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Lien symbolique interdit dans dist : {path.relative_to(source)}")
        if path.is_file() and not path.relative_to(source).as_posix().startswith("data/facts/"):
            files.append(path)
    return files


def recette_headers(data: bytes) -> bytes:
    # Garder les règles de sécurité existantes et insérer noindex dans la règle /*.
    lines = data.decode("utf-8").splitlines(keepends=True)
    if any(line.lstrip().lower().startswith("x-robots-tag:") for line in lines):
        raise ValueError("_headers contient déjà X-Robots-Tag : adaptation explicite requise")
    indices = [i for i, line in enumerate(lines) if line.strip() == "/*"]
    if len(indices) != 1:
        raise ValueError("_headers doit contenir exactement une règle globale /*")
    i = indices[0]
    if not lines[i].endswith("\n"):
        lines[i] += "\n"
    lines.insert(i + 1, ROBOTS_HEADER)
    return "".join(lines).encode("utf-8")


def prepare(source: Path, output: Path, repo: Path = ROOT,
            asset_limit: int = ASSET_LIMIT) -> dict:
    source, output = source.resolve(), output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(f"Snapshot déjà présent : {output}. Choisir une nouvelle destination --output.")
    output = output.resolve()
    if output == source or source in output.parents:
        raise ValueError("La destination ne peut pas être située dans dist/")
    before = git_state(repo)
    files = source_files(source)
    count = sum(path.relative_to(source).as_posix() not in CONTROL_FILES for path in files)
    if count > asset_limit:
        raise ValueError(f"Budget assets dépassé : {count} > {asset_limit}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".preparing-", dir=output.parent))
    entries = []
    try:
        for path in files:
            relative = path.relative_to(source).as_posix()
            original = path.read_bytes()
            data = (recette_headers(original) if relative == "_headers" else
                    b"User-agent: *\nDisallow: /\n" if relative == "robots.txt" else original)
            if path.suffix.lower() in (".html", ".htm"):
                data = recette_links(data)
            target = staging / "dist" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            entries.append({"path": relative, "source_sha256": sha256(original),
                            "sha256": sha256(data), "bytes": len(data),
                            "public_asset": relative not in CONTROL_FILES})
        if not (staging / "dist/_headers").is_file() or not (staging / "dist/robots.txt").is_file():
            raise ValueError("dist doit fournir _headers et robots.txt")
        # Le rafraîchissement local peut tourner : refuser un lot dont les sources
        # ont changé pendant la copie, au lieu de prétendre figer un état cohérent.
        if [p.relative_to(source).as_posix() for p in source_files(source)] != [e["path"] for e in entries]:
            raise ValueError("Liste des sources modifiée pendant la préparation; recommencer")
        for entry in entries:
            if sha256((source / entry["path"]).read_bytes()) != entry["source_sha256"]:
                raise ValueError(f"Source modifiée pendant la préparation : {entry['path']}; recommencer")
        after = git_state(repo)
        if before != after:
            raise ValueError("État Git modifié pendant la préparation; recommencer")
        public = [{k: e[k] for k in ("path", "sha256", "bytes")}
                  for e in entries if e["public_asset"]]
        content_sha = sha256(json.dumps(public, sort_keys=True, separators=(",", ":")).encode())
        snapshot_files = [{k: e[k] for k in ("path", "sha256", "bytes")} for e in entries]
        snapshot_sha = sha256(json.dumps(snapshot_files, sort_keys=True, separators=(",", ":")).encode())
        manifest = {"schema": "aleaquant-recette-snapshot-v1",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "worker": "aleaquant-recette", "source_directory": str(source),
                    "snapshot_directory": str(output), "git": before,
                    "asset_count": count, "asset_limit": asset_limit,
                    "public_content_sha256": content_sha,
                    "snapshot_content_sha256": snapshot_sha, "files": entries,
                    "overlays": [
                        "_headers : X-Robots-Tag noindex, nofollow, noarchive",
                        "robots.txt : User-agent * / Disallow /",
                        "HTML : href de <a> vers aleaquant.org ou aleaquant.aleaquant.workers.dev rendus relatifs à l'origine; autres URL inchangées"],
                    "note": "Git HEAD est un repère; les assets proviennent du dist local, potentiellement dirty."}
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging.rename(output)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "dist")
    parser.add_argument("--output", type=Path, default=ROOT / ".recette/current")
    args = parser.parse_args()
    try:
        manifest = prepare(args.source, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Préparation refusée : {error}\n")
    print(json.dumps({"snapshot": manifest["snapshot_directory"],
                      "asset_count": manifest["asset_count"],
                      "public_content_sha256": manifest["public_content_sha256"],
                      "git_head": manifest["git"]["head"],
                      "git_dirty": manifest["git"]["dirty"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
