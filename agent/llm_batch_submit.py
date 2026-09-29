"""Soumet un batch OpenAI (Batch API, ~50% moins cher que l'appel direct, jusqu'à 24h
de délai) pour reformuler en LLM les brouillons déterministes des N derniers tirages
d'un coup. Fait pour couvrir tout l'historique d'un jeu (~2 000 tirages) sans faire
exploser le budget quotidien.

Lance depuis ton Terminal (accès réseau requis) :
  python3 agent/llm_batch_submit.py --n 2000

Puis, plus tard (le job peut prendre de quelques minutes à 24h ; relance la commande
de récupération jusqu'à ce qu'elle dise "completed") :
  python3 agent/llm_batch_collect.py --batch-id BATCH_ID

Non testé en conditions réelles (je n'ai pas d'accès réseau vers l'API depuis mon
environnement) : si une étape échoue, colle l'erreur complète à Claude.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"
MANIFEST_DIR = ROOT / "runs-llm" / "_batches"

sys.path.insert(0, str(ROOT / "agent"))
from draw_report import write  # noqa: E402

MODEL = "gpt-5.4-mini"


def load_key():
    if not ENV_PATH.exists():
        sys.exit(f"Pas de fichier {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"Pas de OPENAI_API_KEY dans {ENV_PATH}")


def prompt_for(claim_texts):
    return (
        "Tu reformules chaque phrase suivante en français plus naturel, vivant, avec un peu de chaleur, "
        "SANS changer un seul nombre ni une seule unité, SANS ajouter ni retirer d'information factuelle. "
        "Une phrase d'entrée = une phrase de sortie, même ordre, même contenu factuel. "
        "Réponds en JSON strict : {\"rewritten\": [\"...\", ...]} avec exactement "
        f"{len(claim_texts)} éléments dans le même ordre, rien d'autre.\n\nPhrases :\n"
        + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(claim_texts))
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=2000, help="nombre de tirages les plus récents à couvrir")
    ap.add_argument("--out", type=Path, default=ROOT / "runs-llm", help="où iront les brouillons une fois récupérés")
    args = ap.parse_args()

    from openai import OpenAI
    client = OpenAI(api_key=load_key())

    draws = json.loads((ROOT / "dist" / "data" / "draws.json").read_text(encoding="utf-8"))
    rows = draws["rows"][-args.n:]

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    jsonl_path = MANIFEST_DIR / f"batch_input_{stamp}.jsonl"
    manifest = {}
    n_written = 0

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            draw_id = row[0]
            out_path = args.out / draw_id / "draft.json"
            if out_path.exists():
                continue  # déjà fait (mode direct ou batch précédent)
            facts_path = ROOT / "dist" / "data" / "facts" / f"{draw_id}.json"
            if not facts_path.exists():
                continue
            facts = json.loads(facts_path.read_text(encoding="utf-8"))
            title, _, claims = write(facts)
            body = {
                "model": MODEL,
                "input": prompt_for([c["text"] for c in claims]),
                "reasoning": {"effort": "low"},
            }
            f.write(json.dumps({"custom_id": draw_id, "method": "POST", "url": "/v1/responses", "body": body},
                                ensure_ascii=False) + "\n")
            manifest[draw_id] = {"facts_path": str(facts_path), "title": title, "claims": claims}
            n_written += 1

    print(f"{n_written} requêtes préparées dans {jsonl_path}")
    if n_written == 0:
        print("Rien à soumettre (déjà tout fait, ou aucun tirage dans la plage ?).")
        return

    uploaded = client.files.create(file=open(jsonl_path, "rb"), purpose="batch")
    print("fichier envoyé :", uploaded.id)
    batch = client.batches.create(input_file_id=uploaded.id, endpoint="/v1/responses", completion_window="24h")
    print("batch créé :", batch.id, "| statut :", batch.status)

    manifest_out = MANIFEST_DIR / f"{batch.id}.manifest.json"
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("manifeste sauvegardé :", manifest_out)

    print("\nPour récupérer (à relancer jusqu'à ce que ce soit prêt) :")
    print(f"  python3 agent/llm_batch_collect.py --batch-id {batch.id}")


if __name__ == "__main__":
    main()
