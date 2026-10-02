"""Choix d'angle A/B/C avant rédaction d'un rapport de tirage AleaQuant.

Nom : agent/editorial_angle.py · Version : 0.1 · Date : 2026-09-30
Auteur : AleaQuant · Historique : première compétence éditoriale structurée.
TODO : évaluer titres, coût et fluidité du corps sur un lot commun de tirages.

Le modèle propose ; les contrôles déterministes filtrent ; l'humain choisit.
La proposition et la sélection sont des fichiers distincts. Aucun brouillon approuvé
ni article publié n'est modifié par cette commande.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from draw_report import digest, normalize_numbers
from guards import (MODEL, guard_enum_leak, guard_interpretive_words,
                    guard_markdown, lint_language, load_key)

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = Path(__file__).resolve().parent / "prompts" / "editorial_angle.md"
DEFAULT_OUT = ROOT / "runs-angles"
DECADE_RANGE = re.compile(
    r"\b(?:1\s*[-–—]\s*10|11\s*[-–—]\s*20|21\s*[-–—]\s*30|"
    r"31\s*[-–—]\s*40|41\s*[-–—]\s*(?:49|50))\b"
)
GLOBAL_RARE = re.compile(
    r"\b(?:grille|tirage|combinaison|configuration|ensemble)\s+"
    r"(?:très\s+)?(?:rare|exceptionnel|inhabituel)\b", re.IGNORECASE,
)
SPELLED_NUMBERS = {"zéro": "0", "zero": "0", "deux": "2", "trois": "3",
                   "quatre": "4", "cinq": "5", "six": "6", "sept": "7",
                   "huit": "8", "neuf": "9", "dix": "10"}


def facts_for(draw_id):
    if not re.fullmatch(r"[A-Z]{2}-[A-Z0-9-]+", draw_id):
        raise ValueError("identifiant de tirage invalide")
    path = ROOT / "dist" / "data" / "facts" / f"{draw_id}.json"
    raw = path.read_bytes()
    facts = json.loads(raw)
    if facts["draw_id"] != draw_id:
        raise ValueError("identifiant différent dans la fiche de faits")
    return facts, hashlib.sha256(raw).hexdigest()


def title_numbers(text):
    """Normalise les quantités utiles au titre, y compris « quatre dizaines »."""
    words = [SPELLED_NUMBERS[w.lower()] for w in re.findall(r"\b[\wÀ-ÿ]+\b", text)
             if w.lower() in SPELLED_NUMBERS]
    return normalize_numbers(text) | set(words)


def validate_option(option, facts):
    if not isinstance(option, dict) or set(option) != {"id", "title", "angle", "evidence_ids"}:
        raise ValueError("chaque option doit contenir id, title, angle et evidence_ids")
    title, angle, ids = option["title"], option["angle"], option["evidence_ids"]
    if not isinstance(title, str) or not 15 <= len(title.strip()) <= 110 or "\n" in title:
        raise ValueError("titre vide, trop long ou sur plusieurs lignes")
    if not isinstance(angle, str) or not 20 <= len(angle.strip()) <= 300 or "\n" in angle:
        raise ValueError("angle vide, trop long ou sur plusieurs lignes")
    if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or len(ids) != len(set(ids)):
        raise ValueError("un à trois faits distincts sont requis")
    by_id = {f["fact_id"]: f for f in facts["facts"]}
    if any(fid not in by_id for fid in ids):
        raise ValueError("un identifiant de fait est absent du Research Pack")
    subset = {"facts": [by_id[fid] for fid in ids]}
    for text in (title, angle):
        if DECADE_RANGE.search(text):
            raise ValueError("nommer les décades par leur rang, sans plage numérique")
        if GLOBAL_RARE.search(text):
            raise ValueError("ne pas qualifier la grille entière de rare")
        if guard_markdown(text) or guard_enum_leak(text) or lint_language(text):
            raise ValueError("mise en forme, jargon ou promesse interdite")
        if guard_interpretive_words(text, subset):
            raise ValueError("mot de rareté non soutenu par les faits cités")
        allowed = set()
        for f in subset["facts"]:
            allowed |= normalize_numbers(str(f.get("value", "")))
            allowed |= normalize_numbers(f.get("statement", ""))
        unsupported = title_numbers(text) - allowed
        if unsupported:
            raise ValueError(f"quantités absentes des faits cités : {sorted(unsupported)}")
    return option


def validate_options(data, facts):
    options = data.get("options") if isinstance(data, dict) else None
    if not isinstance(options, list) or len(options) != 3:
        raise ValueError("trois propositions A/B/C sont requises")
    if [o.get("id") for o in options if isinstance(o, dict)] != ["A", "B", "C"]:
        raise ValueError("l'ordre des propositions doit être A, B, C")
    seen = set()
    for option in options:
        validate_option(option, facts)
        normalized = re.sub(r"\W+", "", option["title"].casefold())
        if normalized in seen:
            raise ValueError("deux titres identiques")
        seen.add(normalized)
    return options


def build_prompt(facts):
    """Tous les faits sont visibles, même les faits ordinaires intéressants à raconter."""
    selected = [{k: f.get(k) for k in ("fact_id", "statement", "metric", "value", "rarity")
                if k in f} for f in facts["facts"]]
    return (SKILL_PATH.read_text(encoding="utf-8")
            + "\n\nTIRAGE ET FAITS VÉRIFIÉS :\n"
            + json.dumps({"draw_id": facts["draw_id"], "date": facts["date"],
                          "main": facts["main"], "stars": facts["stars"],
                          "facts": selected}, ensure_ascii=False))


def parse_response(text, facts):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    data = json.loads(text)
    return validate_options(data, facts)


def propose(draw_id, response_text, model=MODEL, effort="low", out_dir=DEFAULT_OUT, usage=None):
    facts, facts_sha = facts_for(draw_id)
    options = parse_response(response_text, facts)
    proposal = {"schema": "aleaquant-editorial-angles-v1", "draw_id": draw_id,
                "facts_sha256": facts_sha, "skill": "editorial_angle@0.1",
                "model": model, "effort": effort, "options": options,
                "usage": usage or {}}
    path = Path(out_dir) / draw_id / "angles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def show(path):
    proposal = json.loads(Path(path).read_text(encoding="utf-8"))
    facts, sha = facts_for(proposal["draw_id"])
    if sha != proposal["facts_sha256"]:
        raise ValueError("les faits ont changé depuis la proposition")
    validate_options({"options": proposal["options"]}, facts)
    by_id = {f["fact_id"]: f for f in facts["facts"]}
    for o in proposal["options"]:
        print(f"{o['id']} — {o['title']}\n  {o['angle']}")
        for fid in o["evidence_ids"]:
            print(f"  ↳ {fid} : {by_id[fid]['statement']}")


def choose(path, option_id):
    path = Path(path)
    proposal = json.loads(path.read_text(encoding="utf-8"))
    facts, sha = facts_for(proposal["draw_id"])
    if sha != proposal["facts_sha256"]:
        raise ValueError("les faits ont changé depuis la proposition")
    options = validate_options({"options": proposal["options"]}, facts)
    option = next((o for o in options if o["id"] == option_id), None)
    if option is None:
        raise ValueError("choisir A, B ou C")
    selection = {"schema": "aleaquant-editorial-angle-selection-v1",
                 "draw_id": proposal["draw_id"], "facts_sha256": sha,
                 "proposal_sha256": digest(proposal), "option": option}
    out = path.with_name("selected.json")
    out.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def revise(path, option_id, title):
    """Permet au rédacteur de polir un titre avant le choix, avec les mêmes gardes."""
    path = Path(path)
    if path.with_name("selected.json").exists():
        raise ValueError("une sélection existe déjà : créer une nouvelle proposition avant révision")
    proposal = json.loads(path.read_text(encoding="utf-8"))
    facts, sha = facts_for(proposal["draw_id"])
    if sha != proposal["facts_sha256"]:
        raise ValueError("les faits ont changé depuis la proposition")
    option = next((o for o in proposal["options"] if o["id"] == option_id), None)
    if option is None:
        raise ValueError("choisir A, B ou C")
    option["title"] = title
    validate_options({"options": proposal["options"]}, facts)
    proposal["revised_by_human"] = True
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_selected(path, facts):
    """Contrôle que l'angle choisi correspond toujours aux trois titres et aux faits."""
    path = Path(path)
    selection = json.loads(path.read_text(encoding="utf-8"))
    proposal = json.loads(path.with_name("angles.json").read_text(encoding="utf-8"))
    current, sha = facts_for(facts["draw_id"])
    if sha != selection["facts_sha256"] or sha != proposal["facts_sha256"]:
        raise ValueError("les faits ont changé depuis le choix de titre")
    if selection["proposal_sha256"] != digest(proposal):
        raise ValueError("les propositions ont changé après la sélection")
    options = validate_options({"options": proposal["options"]}, current)
    if selection["option"] not in options or selection["draw_id"] != facts["draw_id"]:
        raise ValueError("la sélection ne correspond pas aux propositions")
    return selection["option"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose", help="demande trois angles au modèle")
    p.add_argument("draw_id")
    p.add_argument("--model", default=MODEL)
    p.add_argument("--effort", default="low")
    p.add_argument("--response-file", type=Path, help="réponse JSON existante, sans appel API")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p = sub.add_parser("show", help="affiche titres et preuves")
    p.add_argument("proposal", type=Path)
    p = sub.add_parser("choose", help="enregistre le choix humain")
    p.add_argument("proposal", type=Path)
    p.add_argument("option", choices=["A", "B", "C"])
    p = sub.add_parser("revise", help="affine un titre avant sélection")
    p.add_argument("proposal", type=Path)
    p.add_argument("option", choices=["A", "B", "C"])
    p.add_argument("--title", required=True)
    args = ap.parse_args()
    if args.cmd == "propose":
        if args.response_file:
            response_text, usage = args.response_file.read_text(encoding="utf-8"), {}
        else:
            from openai import OpenAI
            facts, _ = facts_for(args.draw_id)
            response = OpenAI(api_key=load_key()).responses.create(
                model=args.model, input=build_prompt(facts), reasoning={"effort": args.effort})
            response_text = response.output_text
            usage = {"input_tokens": getattr(response.usage, "input_tokens", None),
                     "output_tokens": getattr(response.usage, "output_tokens", None)}
        path = propose(args.draw_id, response_text, args.model, args.effort, args.out, usage)
        print(path)
        show(path)
    elif args.cmd == "show":
        show(args.proposal)
    elif args.cmd == "revise":
        print(revise(args.proposal, args.option, args.title))
    else:
        print(choose(args.proposal, args.option))


if __name__ == "__main__":
    main()
