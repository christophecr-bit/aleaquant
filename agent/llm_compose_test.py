"""Test v2 : composition analytique réelle (pas une reformulation phrase à phrase).
Donne TOUS les faits calculés au LLM, lui demande de choisir, synthétiser, commenter
la géométrie (concentration/dispersion), et varier la structure d'un article à l'autre.
Garde numérique appliqué sur le texte entier vs l'ensemble des faits (pas par claim).
Garde lexical : les mots interprétatifs (rare, notable, exceptionnel...) doivent être
justifiés par le champ `rarity` réel d'au moins un fait fourni, jamais une impression
libre du modèle.

  python3 agent/llm_compose_test.py EM-26077
  python3 agent/llm_compose_test.py EM-2011053
"""
import json
import re
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
            if "rarity" in f:
                bits.append(f"rareté={f['rarity']}")
            lines.append(" · ".join(bits))
        elif f.get("statement"):
            lines.append(f"{f['fact_id']} — {f['statement']}")
    return "\n".join(lines)


# bornes de tranches de dizaines (domaine 1-50) : reconnues UNIQUEMENT quand elles
# apparaissent comme une plage explicite ("1-10", "11–20", ...), jamais en liste blanche
# globale — sinon un "20" ou "41" isolé ailleurs dans le texte ne serait plus signalé.
DECADE_RANGE_RE = re.compile(r'\b(1|11|21|31|41)\s*[-–—]\s*(10|20|30|40|50)\b')


def decade_range_numbers(text):
    nums = set()
    for m in DECADE_RANGE_RE.finditer(text):
        nums.add(m.group(1))
        nums.add(m.group(2))
    return nums


def guard_full_text(text, facts):
    allowed = normalize_numbers(', '.join(map(str, facts['main'] + facts['stars'])) + ', ' + facts['date'])
    allowed |= {'2', '3', '5', '10'}
    for f in facts['facts']:
        allowed |= normalize_numbers(json.dumps(f, ensure_ascii=False))
        allowed |= normalize_numbers(f.get('statement', ''))
    extra = normalize_numbers(text) - allowed
    extra -= decade_range_numbers(text)
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


# --- garde lexical : mots de rareté/notabilité vs champ `rarity` des faits fournis ---

RARITY_ORDER = {"COMMON": 0, "UNCOMMON": 1, "RARE": 2, "VERY_RARE": 3}

# du plus spécifique/fort au plus faible : évite qu'un motif faible ("rare") ne
# matche à l'intérieur d'un motif fort déjà reconnu ("très rare"). Chaque match
# retenu est effacé du texte avant d'essayer le motif suivant.
INTERPRETIVE_TERMS = [
    (re.compile(r"extrêmement rares?", re.IGNORECASE), "VERY_RARE"),
    (re.compile(r"très rares?", re.IGNORECASE), "VERY_RARE"),
    (re.compile(r"exceptionnelles?|exceptionnels?", re.IGNORECASE), "VERY_RARE"),
    (re.compile(r"rares?", re.IGNORECASE), "RARE"),
    (re.compile(r"notables?", re.IGNORECASE), "RARE"),
    (re.compile(r"frappantes?|frappants?", re.IGNORECASE), "RARE"),
    (re.compile(r"remarquables?", re.IGNORECASE), "RARE"),
    (re.compile(r"peu courantes?|peu courants?", re.IGNORECASE), "UNCOMMON"),
    (re.compile(r"inhabituelles?|inhabituels?", re.IGNORECASE), "UNCOMMON"),
]

NEGATION_RE = re.compile(r"\b(pas|aucun|aucune|sans|ni|jamais)\b", re.IGNORECASE)


def guard_interpretive_words(text, facts):
    """Retourne la liste des mots de rareté employés sans fait assez rare pour les
    justifier. Coarse-grained : vérifie qu'AU MOINS un fait fourni atteint le niveau
    requis, ne tente pas d'apparier le mot au fait précis qu'il décrit — mais ça
    suffit à bloquer une inflation manifeste (ex. "exceptionnel" alors que rien ne
    dépasse RARE).
    """
    max_rarity_available = max(
        (RARITY_ORDER.get(f.get("rarity"), 0) for f in facts["facts"] if "rarity" in f),
        default=0,
    )

    working = text
    unjustified = []
    for pattern, level in INTERPRETIVE_TERMS:
        for m in pattern.finditer(working):
            start = m.start()
            window = working[max(0, start - 30):start]
            if NEGATION_RE.search(window):
                continue  # "ce n'est pas rare" etc. : pas une affirmation de rareté
            if RARITY_ORDER[level] > max_rarity_available:
                unjustified.append((m.group(0), level))
        # efface les matches (justifiés ou non) pour ne pas les re-matcher plus faible
        working = pattern.sub(lambda mm: " " * len(mm.group(0)), working)
    return unjustified


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
3. Relève ce qui est statistiquement notable (classe rare, queue de loi) s'il y en a — sinon dis-le honnêtement, une forme ordinaire est aussi une observation valide. Précise bien QUELLE queue (somme des numéros, des étoiles, etc.) est en jeu, ne généralise pas. Chaque fois que tu qualifies un chiffre de "rare", "peu courant", "notable", "frappant" ou "exceptionnel", reprends EXACTEMENT le niveau donné par le champ rareté= du fait correspondant (COMMON→n'emploie aucun de ces mots, UNCOMMON→"peu courant", RARE→"rare"/"notable", VERY_RARE→"très rare"/"exceptionnel") ; n'amplifie jamais un niveau.
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
    print("\n=== GARDE NUMÉRIQUE (texte entier vs tous les faits) ===")
    print("OK" if not problems else f"NOMBRES NON JUSTIFIÉS : {sorted(problems)}")

    word_problems = guard_interpretive_words(text, facts)
    print("\n=== GARDE LEXICAL (mots de rareté vs champ rarity des faits) ===")
    print("OK" if not word_problems else f"MOTS NON JUSTIFIÉS : {word_problems}")

    usage = resp.usage
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    cost = in_tok / 1e6 * 0.75 + out_tok / 1e6 * 4.50
    print(f"\n=== COÛT === {cost:.5f} $ (in={in_tok} out={out_tok})")


if __name__ == "__main__":
    main()
