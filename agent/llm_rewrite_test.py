"""Test à un seul article : reformulation LLM du brouillon déterministe.
Lance ça toi-même (accès réseau requis) :

  cd ~/aleaquant-web
  python3 -m pip install --user openai   # si pas déjà installé
  python3 agent/llm_rewrite_test.py

Lit la clé dans ../aleaquant-editorial-agents/.env (jamais affichée).
Ne publie rien, n'écrit rien : juste un test, affiche le texte + le coût réel.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"

key = None
for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
    if line.strip().startswith("OPENAI_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
if not key:
    sys.exit(f"Pas de OPENAI_API_KEY dans {ENV_PATH}")

sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "scripts"))
from draw_report import write, guard  # noqa: E402

facts = json.loads((ROOT / "dist" / "data" / "facts" / "EM-26077.json").read_text(encoding="utf-8"))
title, body, claims = write(facts)
claim_texts = [c["text"] for c in claims]

from openai import OpenAI  # noqa: E402

client = OpenAI(api_key=key)

prompt = (
    "Tu reformules chaque phrase suivante en français plus naturel, vivant, avec un peu de chaleur, "
    "SANS changer un seul nombre ni une seule unité, SANS ajouter ni retirer d'information factuelle. "
    "Une phrase d'entrée = une phrase de sortie, même ordre, même contenu factuel. "
    "Réponds en JSON strict : {\"rewritten\": [\"...\", ...]} avec exactement "
    f"{len(claim_texts)} éléments dans le même ordre, rien d'autre.\n\nPhrases :\n"
    + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(claim_texts))
)

MODEL = "gpt-5.4-mini"

def try_responses_api():
    return client.responses.create(model=MODEL, input=prompt, reasoning={"effort": "low"})

def try_chat_api():
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

resp = None
for name, fn in [("responses(reasoning=low)", try_responses_api), ("chat.completions", try_chat_api)]:
    try:
        resp = fn()
        print(f"=== OK via {name} ===")
        break
    except Exception as e:  # noqa: BLE001
        print(f"--- {name} a échoué : {e!r}")

if resp is None:
    sys.exit("Aucune des deux méthodes n'a marché — colle l'erreur complète à Claude.")

text = getattr(resp, "output_text", None) or resp.choices[0].message.content
print("\n--- réponse brute ---")
print(text)

try:
    rewritten = json.loads(text)["rewritten"]
except Exception as e:  # noqa: BLE001
    sys.exit(f"JSON pas parsable ({e}) — colle la réponse brute ci-dessus à Claude.")

if len(rewritten) != len(claim_texts):
    print(f"\n!! ATTENTION : {len(rewritten)} phrases reçues pour {len(claim_texts)} attendues.")

new_claims = [dict(c, text=t) for c, t in zip(claims, rewritten)]
problems = guard(new_claims, facts)

print("\n=== BROUILLON REFORMULÉ ===")
print(title)
print()
for t in rewritten:
    print("-", t)

print("\n=== GARDE NUMÉRIQUE ===")
print("OK" if not problems else f"PROBLÈMES : {problems}")

usage = getattr(resp, "usage", None)
print("\n=== USAGE / COÛT ===")
print(usage)
if usage:
    in_tok = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
    out_tok = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None)
    if in_tok and out_tok:
        cost = in_tok / 1e6 * 0.75 + out_tok / 1e6 * 4.50
        print(f"~{cost:.5f} $ pour cet article (tarif gpt-5.4-mini)")
