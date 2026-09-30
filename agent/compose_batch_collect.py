"""Récupère un batch de rapports de tirage en mode « compose » et écrit les brouillons.

  python3 agent/compose_batch_collect.py --batch-id BATCH_ID

Relancer jusqu'à ce que le statut soit "completed" (de quelques minutes à 24 h).

Chaque réponse passe par la même chaîne déterministe que le mode direct : nettoyage du
markdown, les cinq gardes, puis construction du brouillon au schéma aleaquant-article-v1
avec ses puces de rareté. Pas de relecture ni de réparation en batch (voir
compose_batch_submit.py) : les brouillons dont un garde échoue sont écrits en BLOCKED et
listés en fin de rapport, à reprendre en direct.

Pour vérifier le traitement sans appel réseau, sur un fichier de résultats déjà
téléchargé (ou fabriqué) :
  python3 agent/compose_batch_collect.py --input-file sortie.jsonl --manifest m.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"
OUT_DIR = ROOT / "runs-llm-compose"
MANIFEST_DIR = OUT_DIR / "_batches"

sys.path.insert(0, str(ROOT / "agent"))
from guards import (  # noqa: E402
    build_compose_article, run_all_guards, strip_markdown,
)

PRICE_IN = 0.75 / 1e6 / 2
PRICE_OUT = 4.50 / 1e6 / 2
WRITER_SUFFIX = "-batch"


def load_key():
    if not ENV_PATH.exists():
        sys.exit(f"Pas de fichier {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"Pas de OPENAI_API_KEY dans {ENV_PATH}")


def extract_output_text(body):
    if body.get("output_text"):
        return body["output_text"]
    for item in body.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    return c.get("text", "")
    raise ValueError("forme de réponse inattendue : texte introuvable")


def traiter(contenu, manifest, out_dir):
    """Traite les lignes de résultat. Aucun appel réseau : testable hors ligne."""
    n_ok = n_blocked = n_failed = 0
    cout = 0.0
    bloques = []
    for line in contenu.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        draw_id = rec.get("custom_id")
        info = manifest.get(draw_id)
        if not info:
            print(f"!! {draw_id} absent du manifeste, ignoré")
            n_failed += 1
            continue
        if rec.get("error"):
            print(f"!! {draw_id} : erreur batch — {rec['error']}")
            n_failed += 1
            continue
        body = (rec.get("response") or {}).get("body")
        if not body:
            print(f"!! {draw_id} : pas de corps de réponse")
            n_failed += 1
            continue
        try:
            texte = strip_markdown(extract_output_text(body)).strip()
        except Exception as e:  # noqa: BLE001
            print(f"!! {draw_id} : extraction échouée — {e!r}")
            n_failed += 1
            continue

        facts_path = Path(info["facts_path"])
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        guards = run_all_guards(texte, facts)
        article = build_compose_article(facts_path, facts, texte, guards)
        article["provenance"]["writer"] += WRITER_SUFFIX
        article["provenance"]["mode"] = "batch"
        out = out_dir / draw_id / "draft.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        usage = body.get("usage") or {}
        cout += (usage.get("input_tokens", 0) or 0) * PRICE_IN
        cout += (usage.get("output_tokens", 0) or 0) * PRICE_OUT
        if article["status"] == "BLOCKED":
            n_blocked += 1
            bloques.append((draw_id, article["guard"]["problems"]))
        else:
            n_ok += 1
    return n_ok, n_blocked, n_failed, cout, bloques


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-id")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--input-file", type=Path, help="fichier de résultats local (sans réseau)")
    ap.add_argument("--manifest", type=Path, help="manifeste à utiliser avec --input-file")
    args = ap.parse_args()

    if args.input_file:
        if not args.manifest:
            sys.exit("--input-file exige --manifest")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))["draws"]
        contenu = args.input_file.read_text(encoding="utf-8")
    else:
        if not args.batch_id:
            sys.exit("--batch-id requis (ou --input-file pour un traitement hors ligne)")
        from openai import OpenAI
        client = OpenAI(api_key=load_key())
        batch = client.batches.retrieve(args.batch_id)
        print(f"statut : {batch.status}")
        if batch.status != "completed":
            print(batch)
            return
        manifest_path = MANIFEST_DIR / f"{args.batch_id}.manifest.json"
        if not manifest_path.exists():
            sys.exit(f"Manifeste introuvable : {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["draws"]
        contenu = client.files.content(batch.output_file_id).text

    n_ok, n_blocked, n_failed, cout, bloques = traiter(contenu, manifest, args.out)

    print(f"\nOK={n_ok} | bloqués (garde)={n_blocked} | échecs={n_failed}")
    print(f"Coût mesuré (tarif batch) : {cout:.4f} $")
    print(f"Brouillons dans : {args.out}")
    if bloques:
        print("\nÀ reprendre en direct (le garde a bloqué) :")
        for draw_id, problemes in bloques[:20]:
            print(f"  {draw_id} : {problemes}")
        if len(bloques) > 20:
            print(f"  … et {len(bloques) - 20} autres")
        print("\n  python3 agent/compose_draw_report.py <DRAW_ID> --write")


if __name__ == "__main__":
    main()
