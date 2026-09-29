"""Test v2 : composition analytique réelle (pas une reformulation phrase à phrase).
Donne TOUS les faits calculés au LLM, lui demande de choisir, synthétiser, commenter
la géométrie (concentration/dispersion), et varier la structure d'un article à l'autre.
Garde numérique appliqué sur le texte entier vs l'ensemble des faits (pas par claim).

  python3 agent/llm_compose_test.py EM-26077
  python3 agent/llm_compose_test.py EM-2011053
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"

sys.path.insert(0, str(ROOT / "agent"))
from draw_report import normalize_numbers, pct, date_fr  # noqa: E402


def load_key():
    if not ENV_PATH.exists():
        sys.exit(f"Pas de fichier {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"Pas de OPENAI_API_KEY dans {ENV_PATH}")


def evidence_block(facts):
    lines = []
    for f in facts["facts"]:
        if f.get("metric") is not None:
            bits = [f"{f['fact_id']} — {f.get('label', f['metric'])} : {f['value']}"]
            if "p_class" in f:
                bits.append(f"classe {f['class_size']}/{f['domain_size']} ({pct(f['p_class'])})")
            if "tail" in f and f["tail"] < 1:
                bits.append(f"queue {pct(f['tail'])}")
            lines.append(" · ".join(bits))
        elif f.get("statement"):
            lines.append(f"{f['fact_id']} — {f['statement']}")
    return "\n".join(lines)


def guard_full_text(text, facts):
    allowed = normalize_numbers(', '.join(map(str, facts['main'] + facts['stars'])) + ', ' + facts['date'])
    allowed |= {'2', '3', '5', '10'}
    for f in facts['facts']:
        allowed |= normalize_numbers(json.dumps(f, ensure_ascii=False))
        allowed |= normalize_numbers(f.get('statement', ''))
    extra = normalize_numbers(text) - allowed
    # tolérance pourcentages arrondis (comme guard() existant, version simplifiée)
    cleaned = set()
    for x in extra:
        try:
            v = float(x)
        except ValueError:
            cleaned.add(x)
            continue
        ok = False
        for f in facts['facts']:
            for k in ('p_class', 'tail', 'p_le', 'p_ge'):
                if k in f and abs(100 * f[k] - v) < 0.06:
                    ok = True
        if not ok:
            cleaned.add(x)
    return cleaned


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: llm_compose_test.py EM-XXXXX")
    draw_id = sys.argv[1]
    facts_path = ROOT / "dist" / "data" / "facts" / f"{draw_id}.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))

    main_nums = ' · '.join('%02d' % n for n in facts['main'])
    stars = ' · '.join('%02d' % n for n in facts['stars'])

    prompt = f"""Tu es rédacteur scientifique pour AleaQuant, un site français de vulgarisation sur les probabilités et la combinatoire appliquées à EuroMillions. Ta ligne éditoriale : rigueur, jamais de prédiction, jamais de promesse de gain, chaque nombre cité doit venir des faits fournis ci-dessous.

Tirage du {date_fr(facts['date'])} : {main_nums} ★ {stars}

Faits calculés disponibles (utilise ceux qui sont pertinents, pas besoin de tous les citer) :
{evidence_block(facts)}

Écris un article de 4 à 6 paragraphes qui :
1. Situe le tirage (probabilité de la combinaison exacte).
2. Commente la GÉOMÉTRIE du tirage : les numéros sont-ils plutôt concentrés (proches les uns des autres, dans peu de dizaines) ou dispersés sur l'étendue 1-50 ? Précise les tranches de dizaines que tu utilises (1-10, 11-20, etc.). N'emploie "concentré"/"dispersé"/"notable"/"rare" que si tu peux l'ancrer explicitement à un chiffre fourni (classe, queue, ou comparaison) — jamais comme impression libre.
3. Relève ce qui est statistiquement notable (classe rare, queue de loi) s'il y en a — sinon dis-le honnêtement, une forme ordinaire est aussi une observation valide. Précise bien QUELLE queue (somme des numéros, des étoiles, etc.) est en jeu, ne généralise pas.
4. Situe l'historique EN UTILISANT le fait de signature (F.signature, qui donne une fréquence sur un nombre de tirages antérieurs précis) et le fait d'historique exact (F.history.exact_main) — c'est la référence avec échelle demandée, ne dis jamais que l'historique manque si ces faits sont fournis.
5. Termine sur le rappel qu'aucune de ces mesures ne prédit le prochain tirage — une seule fois, dans un dernier paragraphe court, pas répété ailleurs.

IMPORTANT : varie ta structure et tes formulations, n'utilise pas un patron figé. N'invente, n'arrondis ni ne déduis AUCUN nombre qui n'est pas explicitement dans les faits ci-dessus. Style vivant mais rigoureux, pas de sensationnalisme."""

    from openai import OpenAI
    client = OpenAI(api_key=load_key())
    resp = client.responses.create(model="gpt-5.4-mini", input=prompt, reasoning={"effort": "low"})
    text = resp.output_text

    print("=== ARTICLE COMPOSÉ ===\n")
    print(text)

    problems = guard_full_text(text, facts)
    print("\n=== GARDE (texte entier vs tous les faits) ===")
    print("OK" if not problems else f"NOMBRES NON JUSTIFIÉS : {sorted(problems)}")

    usage = resp.usage
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    cost = in_tok / 1e6 * 0.75 + out_tok / 1e6 * 4.50
    print(f"\n=== COÛT === {cost:.5f} $ (in={in_tok} out={out_tok})")


if __name__ == "__main__":
    main()
