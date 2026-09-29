"""Récupère un batch OpenAI soumis avec llm_batch_submit.py et écrit les brouillons
LLM correspondants (runs-llm/<id>/draft.json), garde numérique inclus.

  python3 agent/llm_batch_collect.py --batch-id BATCH_ID

Si le statut n'est pas "completed", relance la même commande plus tard (jusqu'à 24h).
Non testé en conditions réelles : si le parsing échoue, colle l'erreur à Claude.
"""
import argparse
import datetime as dt
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"
MANIFEST_DIR = ROOT / "runs-llm" / "_batches"

sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "scripts"))
from draw_report import guard  # noqa: E402
from import_article import digest  # noqa: E402

MODEL = "gpt-5.4-mini"
LLM_WRITER = "aleaquant-draw-report-llm-v1-gpt-5.4-mini-batch"
# tarif batch officiel : moitié du tarif direct
PRICE_IN = 0.75 / 1e6 / 2
PRICE_OUT = 4.50 / 1e6 / 2


def load_key():
    if not ENV_PATH.exists():
        sys.exit(f"Pas de fichier {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"Pas de OPENAI_API_KEY dans {ENV_PATH}")


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
                           "facts_path": str(facts_path), "via": "batch"}}


def extract_output_text(body):
    if "output_text" in body and body["output_text"]:
        return body["output_text"]
    for item in body.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    return c.get("text", "")
    raise ValueError("impossible d'extraire le texte de la réponse batch (forme inattendue)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "runs-llm")
    args = ap.parse_args()

    from openai import OpenAI
    client = OpenAI(api_key=load_key())

    batch = client.batches.retrieve(args.batch_id)
    print("statut :", batch.status)
    if batch.status != "completed":
        print("Pas encore terminé — relance cette même commande plus tard.")
        print(batch)
        return

    manifest_path = MANIFEST_DIR / f"{args.batch_id}.manifest.json"
    if not manifest_path.exists():
        sys.exit(f"Manifeste introuvable : {manifest_path} (batch soumis depuis une autre machine ?)")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    output_file_id = batch.output_file_id
    if not output_file_id:
        sys.exit(f"Pas de output_file_id sur ce batch — statut détaillé : {batch}")
    content = client.files.content(output_file_id).text

    n_ok = n_blocked = n_failed = 0
    total_cost = 0.0
    for line in content.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        custom_id = rec.get("custom_id")
        info = manifest.get(custom_id)
        if not info:
            print(f"!! {custom_id} absent du manifeste, ignoré")
            n_failed += 1
            continue
        if rec.get("error"):
            print(f"!! {custom_id} : erreur batch — {rec['error']}")
            n_failed += 1
            continue
        resp_body = (rec.get("response") or {}).get("body")
        if not resp_body:
            print(f"!! {custom_id} : pas de corps de réponse — {rec}")
            n_failed += 1
            continue
        try:
            output_text = extract_output_text(resp_body)
            rewritten = json.loads(output_text)["rewritten"]
        except Exception as e:  # noqa: BLE001
            print(f"!! {custom_id} : parsing échoué — {e!r}")
            n_failed += 1
            continue
        claims = info["claims"]
        if len(rewritten) != len(claims):
            print(f"!! {custom_id} : {len(rewritten)} phrases reçues pour {len(claims)} attendues")
            n_failed += 1
            continue
        facts_path = Path(info["facts_path"])
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        new_claims = [dict(c, text=t) for c, t in zip(claims, rewritten)]
        article = build_article(facts_path, facts, new_claims, info["title"])
        usage = resp_body.get("usage") or {}
        in_tok = usage.get("input_tokens", 0) or 0
        out_tok = usage.get("output_tokens", 0) or 0
        total_cost += in_tok * PRICE_IN + out_tok * PRICE_OUT
        out_path = args.out / custom_id / "draft.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n")
        if article["status"] == "BLOCKED":
            n_blocked += 1
        else:
            n_ok += 1

    print(f"\nOK={n_ok} | bloqués (garde)={n_blocked} | échecs={n_failed}")
    print(f"Coût total mesuré (tarif batch, -50%) : {total_cost:.4f} $")
    print(f"Brouillons dans : {args.out}")


if __name__ == "__main__":
    main()
