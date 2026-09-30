"""AleaQuant · collecte puis calcul local des tirages · version 0.1 (30/09/2026).

Auteur : AleaQuant. Historique : remplace la routine EuroMillions seule par le
SQLite commun EuroMillions/Loto/Keno. TODO : publier Keno après qualification de
son rendu à la demande. Ne commite, ne déploie et n'approuve aucun article.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import fcntl

GAMES = ("euromillions", "loto", "keno")
PREFIXES = {"euromillions": "EM-", "loto": "LO-", "keno": "KE-"}
SCHEMA = "aleaquant-refresh-state-v1"


def log(message: str) -> None:
    when = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"[{when}] {message}", flush=True)


def paths() -> dict[str, Path]:
    web = Path(os.environ.get("WEB_DIR", Path(__file__).resolve().parents[1])).resolve()
    data = Path(os.environ.get("DATA_DIR", web.parent / "aleaquant-data")).resolve()
    lab = Path(os.environ.get("LAB_DIR", web.parent / "loto-keno-lab-generic")).resolve()
    state = Path(os.environ.get(
        "ALEAQUANT_REFRESH_STATE",
        Path.home() / "Library/Application Support/AleaQuant/refresh-state.json",
    )).resolve()
    return {"web": web, "data": data, "lab": lab,
            "store": data / "data/aleaquant.sqlite3", "state": state}


def revisions(store: Path, game: str) -> dict[str, dict]:
    """Dernière révision par identifiant, sans mélanger les jeux."""
    con = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT r.draw_id, r.revision, r.sha, r.body FROM revisions r "
            "WHERE r.game=? AND NOT EXISTS (SELECT 1 FROM revisions newer "
            "WHERE newer.game=r.game AND newer.draw_id=r.draw_id "
            "AND newer.revision>r.revision)", (game,))
        return {did: {"revision": rev, "sha": sha,
                      "date": json.loads(body)["occurred_on"]}
                for did, rev, sha, body in rows}
    finally:
        con.close()


def read_state(path: Path) -> dict:
    if not path.exists():
        return {"schema": SCHEMA, "computed": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != SCHEMA:
        raise ValueError(f"état de rafraîchissement incompatible : {path}")
    return state


def pending(previous: dict | None, current: dict[str, dict], game: str) -> list[str]:
    if previous is None:
        # Première exécution : EuroMillions et Loto sont entièrement reconstruits.
        # Keno reste en qualification ; seules les 30 dernières fiches sont amorcées.
        ordered = sorted(current, key=lambda did: (current[did]["date"], did))
        return ordered[-30:] if game == "keno" else ordered
    return sorted(did for did, item in current.items() if previous.get(did) != item)


def preflight(p: dict[str, Path]) -> list[str]:
    errors = []
    for label in ("web", "data", "lab", "store"):
        if not p[label].exists():
            errors.append(f"{label} absent : {p[label]}")
    if errors:
        return errors
    for module in ("numpy", "yaml"):
        try:
            __import__(module)
        except ImportError:
            errors.append(f"module Python manquant : {module} dans {sys.executable}")
    if errors:
        return errors
    sys.path.insert(0, str(p["data"]))
    from aleaquant_data import charger
    for game in GAMES:
        try:
            config = charger(p["data"] / "games" / f"{game}.yaml")
            url = config.archive_courante()
            if not url.startswith(f"https://{config.host}/"):
                raise ValueError("archive courante hors de l'hôte officiel")
            if not revisions(p["store"], game):
                raise ValueError("aucun tirage en base")
        except Exception as exc:
            errors.append(f"{game} : {exc}")
    for file in (p["lab"] / "src/lottery_games/euromillions/patterns.py",
                 p["web"] / "dist/data/exact_laws.json",
                 p["web"] / "dist/data/laws/regime-5-49.json",
                 p["web"] / "dist/data/laws/regime-6-49.json",
                 p["web"] / "dist/data/laws/regime-16-56.json",
                 p["web"] / "dist/data/laws/regime-20-70.json"):
        if not file.is_file():
            errors.append(f"entrée de calcul absente : {file}")
    return errors


def command(args: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    rendered = " ".join(args[1:])
    log("commande : " + (rendered[:240] + "…" if len(rendered) > 240 else rendered))
    process = subprocess.run(args, cwd=cwd, env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             check=False)
    try:
        payload = json.loads(process.stdout)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if isinstance(payload, dict) and "draws" in payload and "facts" in payload:
        log(f"  {payload['draws']} tirages ; {len(payload['facts'])} fiches de faits")
    else:
        lines = process.stdout.splitlines()
        for line in lines[:30]:
            log("  " + line)
        if len(lines) > 30:
            log(f"  … {len(lines) - 30} lignes supplémentaires omises")
    if process.returncode:
        raise RuntimeError(f"commande échouée ({process.returncode}) : {' '.join(args[1:])}")


def keno_targets(changed: list[str], current: dict[str, dict], facts_dir: Path,
                 *, initial: bool) -> list[str]:
    if initial:
        return changed
    earliest = min(current[did]["date"] for did in changed)
    existing = (path.stem for path in facts_dir.glob("KE-*.json"))
    targets = set(changed)
    targets.update(did for did in existing if did in current and current[did]["date"] >= earliest)
    return sorted(targets)


def verify_facts(game: str, ids: list[str], current: dict[str, dict], p: dict[str, Path],
                 *, pages: bool) -> None:
    for did in ids:
        fact_path = p["web"] / "dist/data/facts" / f"{did}.json"
        fact = json.loads(fact_path.read_text(encoding="utf-8"))
        if (fact["draw_id"] != did or fact["game_id"] != game
                or fact["source"]["revision_sha256"] != current[did]["sha"]):
            raise RuntimeError(f"faits discordants après calcul : {did}")
        if pages:
            page = (p["web"] / "dist/tirages/euromillions" / fact["date"] / "index.html"
                    if game == "euromillions" else
                    p["web"] / "dist/tirages/loto" / did / "index.html")
            html = page.read_text(encoding="utf-8")
            if did not in html or 'class="metric-spark"' not in html:
                raise RuntimeError(f"page de tirage incomplète : {did}")


@contextmanager
def lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("un rafraîchissement est déjà en cours") from exc
        yield


def run(p: dict[str, Path]) -> int:
    state = read_state(p["state"])
    state_changed = False
    env = os.environ.copy()
    env["ALEAQUANT_HISTORY_DB"] = str(p["store"])
    env["ALEAQUANT_LAB"] = str(p["lab"])
    current = {}
    todo = {}
    errors = []
    for game in GAMES:
        try:
            command([sys.executable, "-m", "aleaquant_data", "ingest", game],
                    cwd=p["data"], env=env)
            current[game] = revisions(p["store"], game)
            todo[game] = pending(state["computed"].get(game), current[game], game)
            log(f"{game} : {len(todo[game])} tirage(s) à calculer")
        except Exception as exc:
            errors.append(f"{game} : ingestion : {exc}")
            log("ÉCHEC " + errors[-1])

    if "euromillions" in todo and todo["euromillions"]:
        try:
            command([sys.executable, "engine/build_data.py", "--facts",
                     str(len(current["euromillions"]))], cwd=p["web"], env=env)
            command([sys.executable, "engine/rarity_profiles.py"], cwd=p["web"], env=env)
        except Exception as exc:
            errors.append(f"euromillions : calcul : {exc}")
            log("ÉCHEC " + errors[-1])
            todo.pop("euromillions")
    if "loto" in todo and todo["loto"]:
        try:
            command([sys.executable, "engine/facts_generic.py", "loto"],
                    cwd=p["web"], env=env)
            command([sys.executable, "-c", "import sys; sys.path.insert(0, 'engine'); "
                     "from rarity_profiles import build_par_regime; "
                     "build_par_regime('loto', 'LO')"], cwd=p["web"], env=env)
        except Exception as exc:
            errors.append(f"loto : calcul : {exc}")
            log("ÉCHEC " + errors[-1])
            todo.pop("loto")
    if "keno" in todo and todo["keno"]:
        try:
            targets = keno_targets(todo["keno"], current["keno"],
                                   p["web"] / "dist/data/facts",
                                   initial="keno" not in state["computed"])
            args = [sys.executable, "engine/facts_generic.py", "keno"]
            args += [part for did in targets for part in ("--draw", did)]
            command(args, cwd=p["web"], env=env)
            todo["keno"] = targets
        except Exception as exc:
            errors.append(f"keno : calcul : {exc}")
            log("ÉCHEC " + errors[-1])
            todo.pop("keno")

    if any(todo.get(game) for game in ("euromillions", "loto")):
        try:
            command([sys.executable, "engine/build_pages.py"], cwd=p["web"], env=env)
        except Exception as exc:
            errors.append(f"pages : {exc}")
            log("ÉCHEC " + errors[-1])
            todo.pop("euromillions", None)
            todo.pop("loto", None)

    for game in GAMES:
        if game not in todo:
            continue
        try:
            # Détecte aussi un import concurrent intervenu pendant les calculs.
            if revisions(p["store"], game) != current[game]:
                raise RuntimeError("source modifiée pendant le calcul")
            verify_facts(game, todo[game], current[game], p,
                         pages=game in ("euromillions", "loto"))
            if state["computed"].get(game) != current[game]:
                state["computed"][game] = current[game]
                state_changed = True
            log(f"{game} : faits vérifiés ; {len(current[game])} tirages synchronisés")
        except Exception as exc:
            errors.append(f"{game} : validation : {exc}")
            log("ÉCHEC " + errors[-1])
    if state_changed:
        p["state"].parent.mkdir(parents=True, exist_ok=True)
        temp = p["state"].with_suffix(".tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        temp.replace(p["state"])
    for error in errors:
        log("à reprendre : " + error)
    if errors:
        return 1
    log("terminé localement : aucun commit, déploiement ou article publié")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="préflight sans réseau ni écriture")
    args = parser.parse_args()
    p = paths()
    issues = preflight(p)
    state = read_state(p["state"])
    for game in GAMES:
        if p["store"].exists():
            current = revisions(p["store"], game)
            work = pending(state["computed"].get(game), current, game)
            log(f"{game} : {len(current)} tirages en base ; {len(work)} en attente de calcul")
    if issues:
        for issue in issues:
            log("PRÉFLIGHT INCOMPLET : " + issue)
        return 1
    if args.check:
        log("préflight complet ; aucune ingestion ni calcul lancé")
        return 0
    with lock(Path.home() / "Library/Application Support/AleaQuant/refresh.lock"):
        return run(p)


if __name__ == "__main__":
    sys.exit(main())
