"""Relecture de style contrôlée d'un brouillon AleaQuant avant approbation.

Auteur : AleaQuant · 2026-10-02 · Révision traçabilité : note publique, preuves et SHA de la version relue.

Nom : agent/editorial_polish.py · Version : 0.1 · Date : 2026-09-30
Auteur : AleaQuant · Historique : première passe de fluidité indépendante du Writer.
TODO : évaluer à l'aveugle la fluidité réelle et le taux de rejet sur un lot de tirages.

Produit un nouveau brouillon, avec un nouveau SHA-256 ; ne modifie pas l'original.
"""

import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path

from draw_report import NUMBER, THOUSANDS, digest
from guards import (METHODO_NOTE, MODEL, load_key, paragraph_evidence,
                    run_all_guards, strip_markdown)

SKILL_PATH = Path(__file__).resolve().parent / "prompts" / "editorial_polish.md"
RARITY_WORDS = re.compile(
    r"\b(?:très\s+rares?|peu\s+courant(?:e|es|s)?|rares?|"
    r"courant(?:e|es|s)?|exceptionnel(?:le|les|s)?|inhabituel(?:le|les|s)?)\b",
    re.IGNORECASE,
)


def paragraphs(body):
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def number_counts(text):
    text = THOUSANDS.sub("", THOUSANDS.sub("", text))
    return Counter((n.replace(",", ".").lstrip("0") or "0") for n in NUMBER.findall(text))


def rarity_counts(text):
    return Counter(re.sub(r"\s+", " ", m.group(0).casefold()) for m in RARITY_WORDS.finditer(text))


def build_prompt(article, facts):
    original = article["draft"]["body"].removesuffix(METHODO_NOTE).strip()
    angle = article["draft"].get("editorial_angle") or {}
    return (SKILL_PATH.read_text(encoding="utf-8")
            + "\n\nTITRE CHOISI : " + article["draft"]["title"]
            + "\nANGLE : " + angle.get("angle", "Décrire honnêtement le tirage.")
            + "\n\nFAITS CITÉS PAR LE BROUILLON :\n"
            + json.dumps([f for f in facts["facts"] if f["fact_id"] in
                          {i for c in article["draft"]["claims"] for i in c["evidence_ids"]}],
                         ensure_ascii=False)
            + "\n\nTEXTE À FLUIDIFIER :\n" + original)


def validate_polish(article, proposed, facts):
    original = article["draft"]["body"].removesuffix(METHODO_NOTE).strip()
    proposed = strip_markdown(proposed).strip()
    if proposed.endswith(METHODO_NOTE):
        proposed = proposed.removesuffix(METHODO_NOTE).strip()
    old_parts, new_parts = paragraphs(original), paragraphs(proposed)
    if len(old_parts) != len(new_parts):
        raise ValueError("nombre de paragraphes modifié")
    if number_counts(original) != number_counts(proposed):
        raise ValueError("nombres modifiés ou déplacés en quantité")
    if rarity_counts(original) != rarity_counts(proposed):
        raise ValueError("qualificatifs de rareté modifiés")
    for i, (before, after) in enumerate(zip(old_parts, new_parts), 1):
        if number_counts(before) != number_counts(after):
            raise ValueError(f"nombres déplacés hors du paragraphe {i}")
        if rarity_counts(before) != rarity_counts(after):
            raise ValueError(f"rareté déplacée hors du paragraphe {i}")
    guards = run_all_guards(proposed, facts, editorial_style=True)
    if any(guards.values()):
        raise ValueError("contrôle scientifique ou lexical en échec : "
                         + str({k: v for k, v in guards.items() if v}))
    new_claims = [{"claim_id": f"C{i}", "text": p,
                   "evidence_ids": paragraph_evidence(p, facts)}
                  for i, p in enumerate(new_parts, 1)]
    for i, (old_claim, new_claim) in enumerate(zip(article["draft"]["claims"], new_claims), 1):
        lost = set(old_claim["evidence_ids"]) - set(new_claim["evidence_ids"])
        if lost:
            raise ValueError(f"faits cités perdus du paragraphe {i} : "
                             + ", ".join(sorted(lost)))
    return proposed, new_claims


def polish(path, proposed, output=None, model=MODEL, effort="low", usage=None):
    path = Path(path)
    article = json.loads(path.read_text(encoding="utf-8"))
    if article["status"] != "PENDING_HUMAN" or article["human_decision"] is not None:
        raise ValueError("seul un brouillon en attente de relecture peut être fluidifié")
    if article["draft_sha256"] != digest(article["draft"]):
        raise ValueError("le brouillon a changé depuis sa génération")
    facts_path = Path(article["provenance"]["facts_path"])
    facts_bytes = facts_path.read_bytes()
    if hashlib.sha256(facts_bytes).hexdigest() != article["research_pack"]["facts_sha256"]:
        raise ValueError("la fiche de faits a changé depuis la rédaction")
    facts = json.loads(facts_bytes)
    if facts["draw_id"] != article["research_pack"]["draw_id"]:
        raise ValueError("faits d'un autre tirage")
    text, claims = validate_polish(article, proposed, facts)
    article["draft"]["body"] = text + "\n\n" + METHODO_NOTE
    article["draft"]["claims"] = claims
    if article['draft'].get('methodology'):
        from article_traceability import refresh_review_metadata
        refresh_review_metadata(article, facts)
        if article['status'] == 'BLOCKED':
            raise ValueError('Traçabilité après relecture : ' + '; '.join(article['guard']['problems']))
    article["draft_sha256"] = digest(article["draft"])
    article["provenance"]["polish"] = {"skill": "editorial_polish@0.1",
                                       "model": model, "effort": effort, "usage": usage or {}}
    out = Path(output) if output else path.with_name("draft-polished.json")
    out.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("draft", type=Path)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--effort", default="low")
    ap.add_argument("--response-file", type=Path, help="texte de relecture existant, sans appel API")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    article = json.loads(args.draft.read_text(encoding="utf-8"))
    facts_bytes = Path(article["provenance"]["facts_path"]).read_bytes()
    if hashlib.sha256(facts_bytes).hexdigest() != article["research_pack"]["facts_sha256"]:
        raise ValueError("la fiche de faits a changé depuis la rédaction")
    facts = json.loads(facts_bytes)
    if args.response_file:
        proposed, usage = args.response_file.read_text(encoding="utf-8"), {}
    else:
        from openai import OpenAI
        response = OpenAI(api_key=load_key()).responses.create(
            model=args.model, input=build_prompt(article, facts),
            reasoning={"effort": args.effort})
        proposed = response.output_text
        usage = {"input_tokens": getattr(response.usage, "input_tokens", None),
                 "output_tokens": getattr(response.usage, "output_tokens", None)}
    try:
        out = polish(args.draft, proposed, args.out, args.model, args.effort, usage)
    except ValueError as first_error:
        rejected = args.draft.with_name("polish-candidate-rejected.txt")
        rejected.write_text(proposed, encoding="utf-8")
        if args.response_file:
            raise
        print(f"Première relecture refusée : {first_error}. Correction unique demandée au modèle.")
        original = article["draft"]["body"].removesuffix(METHODO_NOTE).strip()
        repair = (SKILL_PATH.read_text(encoding="utf-8")
                  + f"\n\nTa première version a été refusée : {first_error}. "
                  "Répare la relecture en conservant EXACTEMENT les nombres et mots de "
                  "rareté du texte initial, paragraphe par paragraphe. Ne supprime aucun "
                  "fait cité.\n\nTEXTE INITIAL :\n" + original
                  + "\n\nPREMIÈRE RELECTURE REFUSÉE :\n" + proposed)
        response = OpenAI(api_key=load_key()).responses.create(
            model=args.model, input=repair, reasoning={"effort": args.effort})
        usage["repair_input_tokens"] = getattr(response.usage, "input_tokens", None)
        usage["repair_output_tokens"] = getattr(response.usage, "output_tokens", None)
        out = polish(args.draft, response.output_text, args.out, args.model, args.effort, usage)
    print(out)


if __name__ == "__main__":
    main()
