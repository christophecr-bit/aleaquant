"""Test v2 : composition analytique réelle (pas une reformulation phrase à phrase).
Donne TOUS les faits calculés au LLM, lui demande de choisir, synthétiser, commenter
la géométrie (concentration/dispersion), et varier la structure d'un article à l'autre.

Trois gardes, tous déterministes :
  1. numérique — chaque nombre du texte doit venir des faits (tolérance % arrondis,
     bornes de dizaines reconnues seulement en contexte de plage explicite) ;
  2. lexical — les mots de rareté (rare, notable, exceptionnel...) doivent être
     justifiés par le champ `rarity` d'au moins un fait fourni ;
  3. jargon — aucun nom de code d'enum (COMMON, VERY_RARE...) ne doit apparaître dans
     la prose française.

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

# même mapping que dist/draws.js (RARITY) — le modèle ne doit voir que le français
RARITY_FR = {
    "COMMON": "classe courante",
    "UNCOMMON": "classe peu courante",
    "RARE": "classe rare",
    "VERY_RARE": "classe très rare",
}

# note de méthode ajoutée de façon déterministe : le modèle ne la rédige plus, donc
# elle est identique partout et pourra devenir un encadré commun côté site.
METHODO_NOTE = (
    "Note de méthode — ces mesures décrivent la forme d'un tirage déjà réalisé. "
    "Les tirages sont indépendants : aucune ne permet de prédire le suivant."
)

# métriques mathématiquement dérivées l'une de l'autre : même classe, même p_class,
# donc jamais à citer comme deux preuves indépendantes.
DERIVED_EQUIVALENTS = [
    ("main.span", "main.mean_gap", "écart moyen = étendue / 4 (5 numéros → 4 écarts)"),
]


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
                bits.append(
                    f"classe de {f['class_size']} sur {f['domain_size']} ({pct(f['p_class'])})"
                )
            if "tail" in f and f["tail"] < 1:
                bits.append(f"queue {pct(f['tail'])}")
            if "rarity" in f:
                bits.append(f"rareté={RARITY_FR.get(f['rarity'], f['rarity'])}")
            lines.append(" · ".join(bits))
        elif f.get("statement"):
            lines.append(f"{f['fact_id']} — {f['statement']}")
    return "\n".join(lines)


def redundancy_note(facts):
    """Signale au modèle les paires de métriques présentes ET redondantes entre elles."""
    present = {f.get("metric") for f in facts["facts"]}
    notes = []
    for a, b, why in DERIVED_EQUIVALENTS:
        if a in present and b in present:
            notes.append(f"- {a} et {b} portent la MÊME information ({why}) : même classe, "
                         f"même probabilité. Ne les cite jamais comme deux constats distincts.")
    return "\n".join(notes)


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
# Frontières de mot des deux côtés : "rare" ne doit pas matcher dans "rareté" ni
# dans un nom de code comme "VERY_RARE" (l'underscore est un caractère de mot).
INTERPRETIVE_TERMS = [
    (re.compile(r"\bextrêmement rares?\b", re.IGNORECASE), "VERY_RARE"),
    (re.compile(r"\btrès rares?\b", re.IGNORECASE), "VERY_RARE"),
    (re.compile(r"\bexceptionnelles?\b|\bexceptionnels?\b", re.IGNORECASE), "VERY_RARE"),
    (re.compile(r"\brares?\b", re.IGNORECASE), "RARE"),
    (re.compile(r"\bnotables?\b", re.IGNORECASE), "RARE"),
    (re.compile(r"\bfrappantes?\b|\bfrappants?\b", re.IGNORECASE), "RARE"),
    (re.compile(r"\bremarquables?\b", re.IGNORECASE), "RARE"),
    (re.compile(r"\bpeu courantes?\b|\bpeu courants?\b", re.IGNORECASE), "UNCOMMON"),
    (re.compile(r"\binhabituelles?\b|\binhabituels?\b", re.IGNORECASE), "UNCOMMON"),
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


# --- garde jargon : aucun nom de code d'enum ne doit fuiter dans la prose ---

ENUM_LEAK_RE = re.compile(r"\b(VERY_RARE|UNCOMMON|COMMON|RARE)\b")


def guard_enum_leak(text):
    return sorted(set(ENUM_LEAK_RE.findall(text)))


# --- garde effectifs : chaque "classe de N sur M" et "queue de X %" cités dans le
# texte doivent correspondre à un fait réel. C'est le contrôle fait par fait demandé :
# valeur, effectif de classe, domaine, queue — vérifiés automatiquement, plus à la main.

# nombre français : groupes de chiffres séparés par des espaces (normal, insécable,
# fine insécable), gourmand mais obligé de se terminer sur un chiffre — sinon un
# "2 118 760" serait tronqué au premier "2".
_NUM = r"\d[\d\u00a0\u202f ]*\d|\d"
CLASS_CITATION_RE = re.compile(rf"classe de ({_NUM}) sur ({_NUM})", re.IGNORECASE)
QUEUE_CITATION_RE = re.compile(r"queue[^.%]{0,40}?(\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE)


def _to_int(s):
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def guard_class_citations(text, facts):
    """Vérifie que chaque couple (effectif de classe, domaine) et chaque pourcentage de
    queue cités existent réellement dans les faits. Retourne la liste des écarts."""
    pairs = {(f["class_size"], f["domain_size"]) for f in facts["facts"] if "class_size" in f}
    tails = [f["tail"] for f in facts["facts"] if f.get("tail") is not None]
    problems = []

    for m in CLASS_CITATION_RE.finditer(text):
        n, d = _to_int(m.group(1)), _to_int(m.group(2))
        if n is None or d is None:
            continue
        if (n, d) not in pairs:
            problems.append(f"classe de {n} sur {d} — aucun fait n'a ce couple (effectif, domaine)")

    for m in QUEUE_CITATION_RE.finditer(text):
        v = float(m.group(1).replace(",", "."))
        if not any(abs(100 * t - v) < 0.06 for t in tails):
            problems.append(f"queue de {m.group(1)} % — ne correspond à aucune queue calculée")

    return problems


# --- avertissement (non bloquant) : qualificatif global appliqué au tirage entier ---
# "configuration serrée", "grille regroupée"... : ces jugements portent sur l'ensemble
# alors que chaque mesure a sa propre classe. À relire humainement, pas à bloquer.

GLOBAL_QUALIFIER_RE = re.compile(
    r"\b(configuration|forme d'ensemble|grille|ensemble|tirage)\b[^.]{0,40}?"
    r"\b(serré|serrée|resserré|resserrée|regroupé|regroupée|concentré|concentrée|"
    r"dispersé|dispersée|étalé|étalée|extrême)\b",
    re.IGNORECASE,
)


def warn_global_qualifiers(text):
    return [m.group(0).strip() for m in GLOBAL_QUALIFIER_RE.finditer(text)]


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: llm_compose_test.py EM-XXXXX")
    draw_id = sys.argv[1]
    facts_path = ROOT / "dist" / "data" / "facts" / f"{draw_id}.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))

    main_nums = ' · '.join('%02d' % n for n in facts['main'])
    stars = ' · '.join('%02d' % n for n in facts['stars'])
    redundancy = redundancy_note(facts)
    redundancy_section = f"\nMétriques redondantes à ne pas double-compter :\n{redundancy}\n" if redundancy else ""

    prompt = f"""Tu es rédacteur scientifique pour AleaQuant, un site français de vulgarisation sur les probabilités et la combinatoire appliquées à EuroMillions. Ta ligne éditoriale : rigueur, jamais de prédiction, jamais de promesse de gain, chaque nombre cité doit venir des faits fournis ci-dessous.

Tirage du {date_fr(facts['date'])} : {main_nums} ★ {stars}

Faits calculés disponibles (utilise ceux qui sont pertinents, pas besoin de tous les citer) :
{evidence_block(facts)}
{redundancy_section}
Écris un article de 4 à 6 paragraphes qui :
1. Situe le tirage (probabilité de la combinaison exacte).
2. Commente la GÉOMÉTRIE du tirage : les numéros sont-ils plutôt concentrés (proches les uns des autres, dans peu de dizaines) ou dispersés sur l'étendue 1-50 ? Précise les tranches de dizaines que tu utilises (1-10, 11-20, etc.). Attention au SENS de la mesure : une étendue élevée (proche de 49) signifie dispersé, une étendue faible signifie concentré — ne qualifie jamais une grande étendue de "resserrée" ni l'inverse.
3. Relève ce qui est statistiquement notable (classe rare, queue de loi) s'il y en a — sinon dis-le honnêtement, une forme ordinaire est aussi une observation valide. Précise bien QUELLE mesure est en jeu, ne généralise pas.
4. Situe l'historique EN UTILISANT le fait de signature (F.signature, qui donne une fréquence sur un nombre de tirages antérieurs précis) et le fait d'historique exact (F.history.exact_main) — c'est la référence avec échelle demandée, ne dis jamais que l'historique manque si ces faits sont fournis.
5. NE TERMINE PAS par un rappel du type "ces mesures ne prédisent pas le prochain tirage" : cette note est ajoutée automatiquement après ton texte, ne l'écris pas toi-même.

RÈGLES DE RIGUEUR — à respecter à la lettre :
a. N'invente, n'arrondis ni ne déduis AUCUN nombre absent des faits ci-dessus.
b. Les mots de rareté ("rare", "peu courant", "notable", "exceptionnel", "très rare") reprennent EXACTEMENT le niveau du champ rareté= du fait concerné. Un niveau "courante" interdit tout mot de rareté. N'amplifie jamais.
c. N'écris JAMAIS un nom de code technique (COMMON, UNCOMMON, RARE, VERY_RARE) dans le texte : emploie uniquement les mots français ("courante", "peu courante", "rare", "très rare").
d. Le niveau de rareté d'une métrique ne vaut QUE pour cette métrique. N'écris jamais qu'une "configuration" ou une "forme d'ensemble" est rare en t'appuyant sur le niveau d'une seule mesure : soit tu cites le fait qui classe précisément cet ensemble, soit tu attribues chaque niveau à sa mesure nommée.
e. Chaque pourcentage cité doit être immédiatement suivi de sa base : "classe de X sur Y" ou "queue de la loi" — jamais un pourcentage nu.
f. Quand un fait donne une liste de valeurs (par exemple les écarts ordonnés), cite-les TOUTES ou aucune : ne réduis jamais une liste de quatre valeurs à trois.
g. Les libellés de rareté te sont donnés sous forme de groupe nominal ("classe rare") parce qu'ils qualifient une classe de combinaisons. Si tu les emploies avec un autre nom, accorde correctement l'adjectif ("un écart courant", "une mesure courante") ; n'écris jamais "ce qui est courante". Soigne les accords en genre et en nombre dans tout le texte.
h. Distingue la POSITION sur l'échelle (numéros tous en haut ou en bas de 1-50, lisible dans la répartition par dizaines) de la DISPERSION (étendue, écarts). Ce sont deux notions différentes : des numéros peuvent être tous en haut de grille ET proches les uns des autres. Ne mélange jamais les deux dans un même adjectif.
i. N'écris jamais un pourcentage nu ni détaché de ce qu'il mesure : indique toujours "fréquence de classe" ou "queue de la loi", avec la mesure concernée. Ne place jamais un pourcentage de classe dans la même phrase que la probabilité de la combinaison complète, pour éviter toute confusion entre les deux.
j. Ne qualifie JAMAIS globalement le tirage, la grille, la configuration ou "l'ensemble" (pas de "configuration serrée", "grille regroupée", "forme resserrée") : chaque adjectif géométrique doit être attaché à une mesure nommée et à sa valeur ("l'étendue vaut 15", "les numéros occupent 2 dizaines, toutes dans la moitié haute"). Décris position et dispersion comme deux constats séparés, sans les résumer en un jugement d'ensemble.
k. Varie ta structure et tes formulations d'un article à l'autre, n'utilise pas un patron figé. Style vivant mais rigoureux, pas de sensationnalisme."""

    from openai import OpenAI
    client = OpenAI(api_key=load_key())
    resp = client.responses.create(model="gpt-5.4-mini", input=prompt, reasoning={"effort": "low"})
    text = resp.output_text

    # --- passe de relecture : langue seulement, jamais les chiffres ni les raretés ---
    proof_prompt = f"""Corrige uniquement l'orthographe, la grammaire et les accords du texte ci-dessous (français).

INTERDICTIONS ABSOLUES : ne modifie, n'ajoute ni ne supprime aucun chiffre, aucun pourcentage, aucun identifiant technique, aucun mot de rareté (courant, peu courant, rare, très rare). Ne reformule pas, ne raccourcis pas, ne réorganise pas les paragraphes. Renvoie uniquement le texte corrigé, sans commentaire ni préambule.

TEXTE :
{text}"""
    proof = client.responses.create(model="gpt-5.4-mini", input=proof_prompt, reasoning={"effort": "low"})
    proofed = proof.output_text.strip()

    # contrôle déterministe : la relecture ne doit avoir touché ni les nombres ni les
    # mots de rareté. Sinon on garde le texte d'origine.
    same_numbers = normalize_numbers(proofed) == normalize_numbers(text)
    same_rarity = sorted(w for w, _ in guard_interpretive_words(proofed, {"facts": []})) == \
        sorted(w for w, _ in guard_interpretive_words(text, {"facts": []}))
    if same_numbers and same_rarity:
        final_text = proofed
        proof_status = "appliquée"
    else:
        final_text = text
        proof_status = f"REJETÉE (nombres identiques={same_numbers}, raretés identiques={same_rarity})"

    text = final_text

    print("=== ARTICLE COMPOSÉ ===\n")
    print(text)
    print(f"\n{METHODO_NOTE}")
    print(f"\n[relecture : {proof_status}]")

    problems = guard_full_text(text, facts)
    print("\n=== GARDE NUMÉRIQUE (texte entier vs tous les faits) ===")
    print("OK" if not problems else f"NOMBRES NON JUSTIFIÉS : {sorted(problems)}")

    word_problems = guard_interpretive_words(text, facts)
    print("\n=== GARDE LEXICAL (mots de rareté vs champ rarity des faits) ===")
    print("OK" if not word_problems else f"MOTS NON JUSTIFIÉS : {word_problems}")

    leaks = guard_enum_leak(text)
    print("\n=== GARDE JARGON (noms de code d'enum dans la prose) ===")
    print("OK" if not leaks else f"NOMS DE CODE À TRADUIRE : {leaks}")

    cite_problems = guard_class_citations(text, facts)
    print("\n=== GARDE EFFECTIFS (classes et queues citées vs faits sources) ===")
    print("OK" if not cite_problems else "ÉCARTS :\n  - " + "\n  - ".join(cite_problems))

    warns = warn_global_qualifiers(text)
    print("\n=== AVERTISSEMENT (qualificatif global sur le tirage, à relire) ===")
    print("aucun" if not warns else "\n  - ".join([""] + warns).strip())

    in_tok = sum((getattr(r.usage, "input_tokens", 0) or 0) for r in (resp, proof))
    out_tok = sum((getattr(r.usage, "output_tokens", 0) or 0) for r in (resp, proof))
    cost = in_tok / 1e6 * 0.75 + out_tok / 1e6 * 4.50
    print(f"\n=== COÛT === {cost:.5f} $ (in={in_tok} out={out_tok})")


if __name__ == "__main__":
    main()
