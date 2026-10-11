"""AleaQuant · collecte puis calcul local des tirages · version 0.6 (02/10/2026).

Auteur : AleaQuant. Historique : v0.1 a remplacé la routine EuroMillions seule par
SQLite commun aux trois jeux ; v0.2 validait les lois et profils par régime. v0.3 bloque
les grandes lois manquantes sans option explicite ; v0.4 ajoute le rattrapage explicite
des faits Keno historiques ; v0.5 vérifie les fiches Keno actives après leur rendu ;
v0.6 unifie la construction des facts sous le moteur YAML pour les trois jeux.
TODO : automatiser le pipeline éditorial léger des tirages.
Ne commite, ne déploie et n'approuve aucun article.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
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
LAW_SCHEMA = "aleaquant-regime-laws-v1"


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
                 p["web"] / "dist/data/exact_laws.json"):
        if not file.is_file():
            errors.append(f"entrée de calcul absente : {file}")
    for game in GAMES:
        if not (p["data"] / "games" / f"{game}.yaml").is_file():
            errors.append(f"configuration absente : {p['data'] / 'games' / f'{game}.yaml'}")
    return errors


def regimes(config) -> set[tuple[int, int]]:
    """Régimes composante (k,n) distincts déclarés dans la configuration du jeu."""
    return {(int(k), int(n)) for rule in config.rules
            for component, k in rule.picks.items()
            if (n := rule.domains.get(component)) is not None and int(k) > 1}


def validate_law_document(document: dict, k: int, domain: int) -> None:
    """Vérifie le contrat combinatoire et la masse de chaque loi disponible."""
    expected = math.comb(domain, k)
    if (document.get("schema") != LAW_SCHEMA or document.get("picks") != k
            or document.get("domain") != domain or document.get("total") != expected):
        raise ValueError(f"métadonnées ou total invalides pour le régime {k}/{domain}")
    laws = document.get("laws")
    fields = document.get("fields")
    missing = document.get("missing_fields", [])
    if not isinstance(laws, dict) or not isinstance(fields, list) or not isinstance(missing, list):
        raise ValueError(f"structure de loi invalide pour le régime {k}/{domain}")
    if (len(fields) != len(set(fields)) or len(missing) != len(set(missing))
            or set(fields) != set(laws) or set(fields) & set(missing)):
        raise ValueError(f"index des champs incohérent pour le régime {k}/{domain}")
    for field, bins in laws.items():
        if (not isinstance(bins, dict)
                or any(type(count) is not int or count < 0 for count in bins.values())
                or sum(bins.values()) != expected):
            raise ValueError(f"masse invalide pour {field} en régime {k}/{domain}")


def ensure_laws(p: dict[str, Path], *, build_large: bool = False,
                allow_build: bool = True) -> None:
    """Valide les lois des règles déclarées; ne lance pas implicitement de gros calcul.

    Un régime manquant est construit automatiquement si son espace est sous le plafond
    d'énumération. Au-delà, l'opérateur doit demander explicitement --build-missing-laws.
    Les régimes incomplets connus (ex. 20/70) restent signalés par missing_fields.
    """
    sys.path.insert(0, str(p["data"]))
    sys.path.insert(0, str(p["web"] / "engine"))
    from aleaquant_data import charger
    from laws import PLAFOND_ENUMERATION, construire, chemin_loi

    output = p["web"] / "dist/data/laws"
    for game in GAMES:
        config = charger(p["data"] / "games" / f"{game}.yaml")
        for k, domain in sorted(regimes(config)):
            path = chemin_loi(k, domain, output)
            if not path.exists():
                if not allow_build:
                    raise RuntimeError(f"loi absente pour {game} ({k}/{domain}) : {path}")
                if math.comb(domain, k) > PLAFOND_ENUMERATION and not build_large:
                    raise RuntimeError(
                        f"loi absente pour {game} ({k}/{domain}); lancer explicitement "
                        "refresh_draws.py --build-missing-laws après qualification du coût")
                document, created = construire(k, domain, output)
                if created:
                    log(f"loi {k}/{domain} construite : {len(document['fields'])} champs")
            else:
                document = json.loads(path.read_text(encoding="utf-8"))
            validate_law_document(document, k, domain)
            if document.get("missing_fields"):
                log(f"loi {game} {k}/{domain} : champs explicitement absents "
                    f"{', '.join(document['missing_fields'])}")


def profile_command(game: str, prefix: str) -> list[str]:
    """Commande commune de profil par jeu/régime, indépendante du moteur de collecte."""
    code = ("import sys; sys.path.insert(0, 'engine'); "
            "from rarity_profiles import build_par_regime; "
            f"build_par_regime('{game}', '{prefix}')")
    return [sys.executable, "-c", code]


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


def keno_fact_coverage(current: dict[str, dict], facts_dir: Path) -> tuple[int, int]:
    """Compte les faits Keno présents avec leur empreinte de source actuelle."""
    valid = 0
    for did, revision in current.items():
        path = facts_dir / f"{did}.json"
        if not path.is_file():
            continue
        try:
            fact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (fact.get("draw_id") == did
                and fact.get("source", {}).get("revision_sha256") == revision["sha"]):
            valid += 1
    return valid, len(current)


def verify_facts(game: str, ids: list[str], current: dict[str, dict], p: dict[str, Path],
                 *, pages: bool) -> None:
    for did in ids:
        fact_path = p["web"] / "dist/data/facts" / f"{did}.json"
        fact = json.loads(fact_path.read_text(encoding="utf-8"))
        if (fact["draw_id"] != did or fact["game_id"] != game
                or fact["source"]["revision_sha256"] != current[did]["sha"]):
            raise RuntimeError(f"faits discordants après calcul : {did}")
        if pages and (game != "keno" or fact.get("rule_id") == "keno-56-16-v1"):
            page = (p["web"] / "dist/tirages/euromillions" / fact["date"] / "index.html"
                    if game == "euromillions" else
                    p["web"] / "dist/tirages/loto" / did / "index.html"
                    if game == "loto" else
                    p["web"] / "dist/tirages/keno" / did / "index.html")
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


def run(p: dict[str, Path], *, build_missing_laws: bool = False,
        backfill_keno_facts: bool = False) -> int:
    state = read_state(p["state"])
    state_changed = False
    env = os.environ.copy()
    env["ALEAQUANT_HISTORY_DB"] = str(p["store"])
    env["ALEAQUANT_LAB"] = str(p["lab"])
    try:
        ensure_laws(p, build_large=build_missing_laws)
    except Exception as exc:
        log(f"ÉCHEC lois : {exc}")
        return 1
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
            command([sys.executable, "engine/build_data.py", "--skip-facts"],
                    cwd=p["web"], env=env)
            command([sys.executable, "engine/rarity_profiles.py"], cwd=p["web"], env=env)
            command(profile_command("euromillions", PREFIXES["euromillions"]),
                    cwd=p["web"], env=env)
            args = [sys.executable, "engine/facts_generic.py", "euromillions"]
            if len(todo["euromillions"]) < len(current["euromillions"]):
                args += [part for did in todo["euromillions"] for part in ("--draw", did)]
            command(args, cwd=p["web"], env=env)
        except Exception as exc:
            errors.append(f"euromillions : calcul : {exc}")
            log("ÉCHEC " + errors[-1])
            todo.pop("euromillions")
    if "loto" in todo and todo["loto"]:
        try:
            args = [sys.executable, "engine/facts_generic.py", "loto"]
            if len(todo["loto"]) < len(current["loto"]):
                args += [part for did in todo["loto"] for part in ("--draw", did)]
            command(args, cwd=p["web"], env=env)
            command(profile_command("loto", PREFIXES["loto"]), cwd=p["web"], env=env)
        except Exception as exc:
            errors.append(f"loto : calcul : {exc}")
            log("ÉCHEC " + errors[-1])
            todo.pop("loto")
    if "keno" in todo and (todo["keno"] or backfill_keno_facts):
        try:
            args = [sys.executable, "engine/facts_generic.py", "keno"]
            if backfill_keno_facts:
                # Sans --draw, le moteur reconstruit l'historique complet dans l'ordre
                # chronologique, nécessaire aux comparaisons antérieures sans look-ahead.
                targets = sorted(current["keno"])
                log(f"keno : rattrapage explicite des faits de {len(targets)} tirages")
                args.append("--force")
            else:
                targets = keno_targets(todo["keno"], current["keno"],
                                       p["web"] / "dist/data/facts",
                                       initial="keno" not in state["computed"])
                args += [part for did in targets for part in ("--draw", did)]
            command(args, cwd=p["web"], env=env)
            command(profile_command("keno", PREFIXES["keno"]), cwd=p["web"], env=env)
            todo["keno"] = targets
        except Exception as exc:
            errors.append(f"keno : calcul : {exc}")
            log("ÉCHEC " + errors[-1])
            todo.pop("keno")

    if any(todo.get(game) for game in GAMES):
        try:
            command([sys.executable, "engine/build_pages.py"], cwd=p["web"], env=env)
        except Exception as exc:
            errors.append(f"pages : {exc}")
            log("ÉCHEC " + errors[-1])
            for game in GAMES:
                todo.pop(game, None)

    for game in GAMES:
        if game not in todo:
            continue
        try:
            # Détecte aussi un import concurrent intervenu pendant les calculs.
            if revisions(p["store"], game) != current[game]:
                raise RuntimeError("source modifiée pendant le calcul")
            verify_facts(game, todo[game], current[game], p,
                         pages=True)
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
    parser.add_argument("--build-missing-laws", action="store_true",
                        help="autorise la construction des lois de grands régimes absents")
    parser.add_argument("--backfill-keno-facts", action="store_true",
                        help="recalcule explicitement les faits de tout l'historique Keno")
    args = parser.parse_args()
    p = paths()
    issues = preflight(p)
    state = read_state(p["state"])
    for game in GAMES:
        if p["store"].exists():
            current = revisions(p["store"], game)
            work = pending(state["computed"].get(game), current, game)
            log(f"{game} : {len(current)} tirages en base ; {len(work)} en attente de calcul")
            if game == "keno":
                valid, total = keno_fact_coverage(
                    current, p["web"] / "dist/data/facts")
                log(f"keno : faits à empreinte courante {valid}/{total} ; "
                    "le rattrapage complet est explicite")
    if issues:
        for issue in issues:
            log("PRÉFLIGHT INCOMPLET : " + issue)
        return 1
    if args.check:
        try:
            ensure_laws(p, allow_build=False)
        except Exception as exc:
            log(f"PRÉFLIGHT INCOMPLET : lois : {exc}")
            return 1
        log("préflight complet ; aucune ingestion ni calcul lancé")
        return 0
    with lock(Path.home() / "Library/Application Support/AleaQuant/refresh.lock"):
        return run(p, build_missing_laws=args.build_missing_laws,
                   backfill_keno_facts=args.backfill_keno_facts)


if __name__ == "__main__":
    sys.exit(main())
