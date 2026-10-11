"""Soumet un batch OpenAI pour composer les rapports de tirage en mode « compose ».

Batch API : ~50 % moins cher que l'appel direct, délai jusqu'à 24 h. Pensé pour couvrir
tout l'historique d'un jeu (~2 000 tirages) sans exploser le budget.

Différences assumées avec le mode direct (agent/compose_draw_report.py) :
  - PAS de relecture de langue ni de passe de réparation : ce sont des appels
    supplémentaires qui dépendent de la réponse précédente, or un batch est one-shot.
    Les brouillons dont un garde échoue sont écrits en BLOCKED et listés à la collecte,
    à reprendre individuellement en direct (le coût unitaire y est négligeable).
  - Le prompt de base est partagé avec le mode direct sans angle expérimental :
    compose_prompt() est importé, pas recopié.

Depuis ton Terminal (accès réseau requis) :
  python3 agent/compose_batch_submit.py --n 50 --dry-run    # vérifie sans rien envoyer
  python3 agent/compose_batch_submit.py --n 2000
  python3 agent/compose_batch_collect.py --batch-id BATCH_ID
"""
import argparse
from hashlib import sha256
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"
OUT_DIR = ROOT / "runs-llm-compose"
MANIFEST_DIR = OUT_DIR / "_batches"

sys.path.insert(0, str(ROOT / "agent"))
from compose_draw_report import compose_prompt  # noqa: E402
from guards import MODEL  # noqa: E402

PRICE_IN = 0.75 / 1e6 / 2   # tarif batch : moitié du direct
PRICE_OUT = 4.50 / 1e6 / 2


def load_key():
    if not ENV_PATH.exists():
        sys.exit(f"Pas de fichier {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"Pas de OPENAI_API_KEY dans {ENV_PATH}")


def build_jsonl(rows, out_dir, force=False):
    """Construit les lignes de requête et le manifeste. Aucune sortie réseau."""
    lignes, manifest, ignores = [], {}, 0
    for row in rows:
        draw_id = row[0]
        if not force and (out_dir / draw_id / "draft.json").exists():
            ignores += 1
            continue
        facts_path = ROOT / "dist" / "data" / "facts" / f"{draw_id}.json"
        if not facts_path.exists():
            ignores += 1
            continue
        facts_bytes = facts_path.read_bytes()
        facts = json.loads(facts_bytes)
        prompt = compose_prompt(facts)
        lignes.append({
            "custom_id": draw_id, "method": "POST", "url": "/v1/responses",
            "body": {"model": MODEL, "input": prompt,
                     "reasoning": {"effort": "low"}},
        })
        manifest[draw_id] = {"facts_path": str(facts_path), "date": facts["date"],
                             "facts_sha256": sha256(facts_bytes).hexdigest(),
                             "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest()}
    return lignes, manifest, ignores


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=2000, help="nombre de tirages les plus récents à couvrir")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--force", action="store_true", help="régénère même si le brouillon existe")
    ap.add_argument("--model", default=MODEL, help="modèle Batch API (défaut inchangé)")
    ap.add_argument("--reasoning-effort", default="low",
                    choices=("none", "minimal", "low", "medium", "high"),
                    help="effort de raisonnement du modèle")
    ap.add_argument("--completion-window", default="24h", choices=("24h",))
    ap.add_argument("--workflow-config-sha", default=None,
                    help="empreinte du profil de publication du dépôt des agents")
    ap.add_argument("--dry-run", action="store_true",
                    help="écrit le JSONL et le manifeste, n'envoie rien, estime le coût")
    args = ap.parse_args()

    draws = json.loads((ROOT / "dist" / "data" / "draws.json").read_text(encoding="utf-8"))
    rows = draws["rows"][-args.n:]
    lignes, manifest, ignores = build_jsonl(rows, args.out, args.force)
    for ligne in lignes:
        ligne["body"]["model"] = args.model
        ligne["body"]["reasoning"]["effort"] = args.reasoning_effort

    if not lignes:
        sys.exit(f"Rien à soumettre ({ignores} tirages déjà traités ou sans faits).")

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    jsonl_path = MANIFEST_DIR / f"compose_input_{stamp}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")

    # estimation grossière : ~4 caractères par token en français, ~900 tokens de sortie
    tok_in = sum(len(l["body"]["input"]) for l in lignes) / 4
    estim = tok_in * PRICE_IN + len(lignes) * 900 * PRICE_OUT if args.model == MODEL else None
    taille = jsonl_path.stat().st_size / 1e6
    cout = f"coût estimé ~{estim:.2f} $ (tarif batch)" if estim is not None else (
        "coût non estimé : tarif à renseigner pour ce modèle")
    print(f"{len(lignes)} requêtes · {ignores} ignorées · {taille:.1f} Mo · {cout}")
    print(f"JSONL : {jsonl_path}")

    if args.dry_run:
        print("\n--dry-run : rien n'a été envoyé.")
        return

    from openai import OpenAI
    client = OpenAI(api_key=load_key())
    with jsonl_path.open("rb") as batch_file:
        up = client.files.create(file=batch_file, purpose="batch")
    batch = client.batches.create(input_file_id=up.id, endpoint="/v1/responses",
                                  completion_window=args.completion_window)
    (MANIFEST_DIR / f"{batch.id}.manifest.json").write_text(
        json.dumps({"batch_id": batch.id, "model": args.model,
                    "reasoning_effort": args.reasoning_effort,
                    "completion_window": args.completion_window, "mode": "compose",
                    "workflow_config_sha256": args.workflow_config_sha,
                    "created": stamp, "draws": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\nbatch soumis : {batch.id} · statut {batch.status}")
    print(f"récupération : python3 agent/compose_batch_collect.py --batch-id {batch.id}")


if __name__ == "__main__":
    main()
