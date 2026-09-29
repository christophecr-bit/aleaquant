"""Reformule en LLM les brouillons déterministes des N derniers tirages.

Coût mesuré au test : ~0,0022 $/article (gpt-5.4-mini, reasoning effort low).
N'écrit QUE des brouillons dans runs-llm/<id>/draft.json ; rien n'est publié.
Le garde numérique du mode template s'applique tel quel : tout brouillon avec
un nombre non justifié passe en statut BLOCKED et ne pourra pas être approuvé.

Lance depuis ton Terminal (accès réseau requis) :
  python3 agent/llm_rewrite_batch.py --n 100

Puis, comme pour le mode template :
  python3 agent/draw_report.py show runs-llm/EM-XXXXX/draft.json
  python3 agent/draw_report.py approve runs-llm/EM-XXXXX/draft.json --reviewer Christophe
"""
import argparse
import datetime as dt
import json
import sys
import time
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"

sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "scripts"))
from draw_report import write, guard  # noqa: E402
from import_article import digest  # noqa: E402

MODEL = "gpt-5.4-mini"
LLM_WRITER = "aleaquant-draw-report-llm-v1-gpt-5.4-mini"
PRICE_IN = 0.75 / 1e6
PRICE_OUT = 4.50 / 1e6


def load_key():
    if not ENV_PATH.exists():
        sys.exit(f"Pas de fichier {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"Pas de OPENAI_API_KEY dans {ENV_PATH}")


def rewrite_claims(client, claim_texts):
    prompt = (
        "Tu reformules chaque phrase suivante en français plus naturel, vivant, avec un peu de chaleur, "
        "SANS changer un seul nombre ni une seule unité, SANS ajouter ni retirer d'information factuelle. "
        "Une phrase d'entrée = une phrase de sortie, même ordre, même contenu factuel. "
        "Réponds en JSON strict : {\"rewritten\": [\"...\", ...]} avec exactement "
        f"{len(claim_texts)} éléments dans le même ordre, rien d'autre.\n\nPhrases :\n"
        + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(claim_texts))
    )
    resp = client.responses.create(model=MODEL, input=prompt, reasoning={"effort": "low"})
    data = json.loads(resp.output_text)
    rewritten = data["rewritten"]
    usage = resp.usage
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    cost = in_tok * PRICE_IN + out_tok * PRICE_OUT
    return rewritten, cost


def build_article(facts_path, facts, claims, title):
    facts_bytes = facts_path.read_bytes()
    used = sorted({i for c in claims for i in c["evidence_ids"]})
    research_pack = {
        "question": "Que dit la forme du tirage %s, sans prétendre prédire le suivant ?" % facts["draw_id"],
        "draw_id": facts["draw_id"], "facts_schema": facts["schema"],
        "facts_sha256": sha256(facts_bytes).hexdigest(), "engine": facts["engine"],
        "evidence": [{"evidence_id": f["fact_id"], "claim": f["statement"], "method": f["method"],
                      "category": f["category"]} for f in facts["facts"] if f["fact_id"] in used],
    }
    body = "\n\n".join(c["text"] for c in claims)
    problems = guard(claims, facts)
    d = {"title": title, "body": body, "claims": claims, "writer": LLM_WRITER,
         "research_pack_sha256": digest(research_pack)}
    return {"schema": "aleaquant-article-v1", "article_id": "tirage-" + facts["draw_id"],
            "kind": "draw_report", "status": "PENDING_HUMAN" if not problems else "BLOCKED",
            "guard": {"problems": problems}, "draft_sha256": digest(d), "draft": d,
            "research_pack": research_pack, "human_decision": None,
            "provenance": {"writer": LLM_WRITER, "model": MODEL,
                           "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                           "facts_path": str(facts_path)}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=100, help="nombre de tirages les plus récents à traiter")
    ap.add_argument("--out", type=Path, default=ROOT / "runs-llm")
    ap.add_argument("--force", action="store_true", help="régénère même si le brouillon existe déjà")
    args = ap.parse_args()

    from openai import OpenAI
    client = OpenAI(api_key=load_key())

    draws = json.loads((ROOT / "dist" / "data" / "draws.json").read_text(encoding="utf-8"))
    rows = draws["rows"][-args.n:]

    total_cost = 0.0
    n_ok = n_blocked = n_skipped = n_failed = 0
    t0 = time.time()

    for i, row in enumerate(rows, 1):
        draw_id = row[0]
        out_path = args.out / draw_id / "draft.json"
        if out_path.exists() and not args.force:
            n_skipped += 1
            continue
        facts_path = ROOT / "dist" / "data" / "facts" / f"{draw_id}.json"
        if not facts_path.exists():
            print(f"[{i}/{len(rows)}] !! facts manquants pour {draw_id}")
            n_failed += 1
            continue
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        title, _, claims = write(facts)
        try:
            rewritten, cost = rewrite_claims(client, [c["text"] for c in claims])
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(rows)}] !! échec LLM pour {draw_id} : {e!r}")
            n_failed += 1
            continue
        if len(rewritten) != len(claims):
            print(f"[{i}/{len(rows)}] !! {draw_id} : {len(rewritten)} phrases pour {len(claims)} attendues, ignoré")
            n_failed += 1
            continue
        new_claims = [dict(c, text=t) for c, t in zip(claims, rewritten)]
        article = build_article(facts_path, facts, new_claims, title)
        total_cost += cost
        if article["status"] == "BLOCKED":
            n_blocked += 1
            print(f"[{i}/{len(rows)}] {draw_id} : BLOQUÉ par le garde — {article['guard']['problems']}")
        else:
            n_ok += 1
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n")
        if i % 10 == 0 or i == len(rows):
            print(f"[{i}/{len(rows)}] ok={n_ok} bloqués={n_blocked} échecs={n_failed} "
                  f"skip={n_skipped} coût cumulé={total_cost:.4f} $")

    dt_s = time.time() - t0
    print("\n=== TERMINÉ ===")
    print(f"OK : {n_ok} | bloqués (garde) : {n_blocked} | échecs : {n_failed} | déjà faits (skip) : {n_skipped}")
    print(f"Coût total mesuré : {total_cost:.4f} $ en {dt_s:.0f} s")
    print(f"Brouillons dans : {args.out}")


if __name__ == "__main__":
    main()
