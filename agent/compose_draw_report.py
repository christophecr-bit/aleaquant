"""Rapport de tirage — chaîne de production (mode « compose »).

Donne TOUS les faits calculés au modèle, annotés de leur niveau de rareté ET de leur
position par rapport à la référence de leur propre mesure, puis lui demande de choisir,
synthétiser et commenter. Ce fichier s'appelait llm_compose_test.py : ce n'est plus un
test, c'est la chaîne qui produit les articles publiés (premier article : EM-2011053,
30/09/2026).

Cinq gardes, tous déterministes :
  1. numérique — chaque nombre du texte doit venir des faits (tolérance sur les
     pourcentages arrondis ; les bornes de dizaines ne sont acceptées que dans un
     contexte de plage explicite, jamais en liste blanche globale) ;
  2. lexical — un mot de rareté (rare, très rare, notable, exceptionnel, peu courant,
     inhabituel ; négations ignorées) n'est autorisé que si une mesure DÉPASSE la
     référence de sa propre distribution (dist/data/rarity_profiles.json). Comparer au
     maximum brut de tous les faits rendait ce garde inopérant : main.sorted_gaps est
     très rare pour tout tirage possible ;
  3. jargon — aucun nom de code (COMMON, VERY_RARE...) dans la prose française ;
  4. effectifs — chaque « classe de N sur M » et chaque « queue de X % » cités doivent
     exister dans les faits ;
  5. mise en forme — aucun marqueur markdown, le site rend le corps en textContent.

Plus une relecture de langue (rejetée si elle touche un chiffre ou un mot de rareté),
une passe de réparation quand un garde bloque, une note de méthode constante, et des
puces de rareté calculées ici, jamais rédigées par le modèle.

  python3 agent/compose_draw_report.py EM-26077 --write
  python3 agent/draw_report.py show runs-llm-compose/EM-26077/draft.json
  python3 agent/draw_report.py approve runs-llm-compose/EM-26077/draft.json --reviewer "..."

Pour tout l'historique à moitié prix, voir compose_batch_submit.py / _collect.py.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"

sys.path.insert(0, str(ROOT / "agent"))
from draw_report import normalize_numbers, pct, date_fr  # noqa: E402

# même mapping que dist/draws.js (RARITY) — le modèle ne doit voir que le français
MODEL = "gpt-5.4-mini"
COMPOSE_WRITER = "aleaquant-draw-report-compose-v1-gpt-5.4-mini"

RARITY_ORDER = {"COMMON": 0, "UNCOMMON": 1, "RARE": 2, "VERY_RARE": 3}

RARITY_FR = {
    "COMMON": "classe courante",
    "UNCOMMON": "classe peu courante",
    "RARE": "classe rare",
    "VERY_RARE": "classe très rare",
}

# note de méthode ajoutée de façon déterministe : le modèle ne la rédige plus, donc
# elle est identique partout et pourra devenir un encadré commun côté site.
METHODO_NOTE = (
    "Note de méthode — ces mesures décrivent la forme d'un tirage déjà réalisé et ne "
    "portent que sur lui. Le modèle probabiliste employé ici suppose des tirages "
    "indépendants et équiprobables : c'est une hypothèse sur le mécanisme de tirage, "
    "pas un résultat démontré par ces mesures. Sous cette hypothèse, aucune d'entre "
    "elles n'aide à anticiper un tirage futur."
)

# dictionnaire des métriques du site (dist/metrics.json) : noms et définitions
# officiels en français, réutilisés tels quels pour que le modèle n'improvise ni le
# terme ni sa définition ("collision de finales" -> "paires de mêmes unités").
def load_metric_dict():
    path = ROOT / "dist" / "metrics.json"
    if not path.exists():
        return {}
    out = {}
    for m in json.loads(path.read_text(encoding="utf-8")):
        key = re.sub(r"@v\d+$", "", re.sub(r"^euromillions\.", "", m["id"]))
        out[key] = (m.get("name", ""), m.get("definition", ""))
    return out


METRIC_DICT = load_metric_dict()


def load_rarity_profiles():
    """Profil de rareté par mesure (engine/rarity_profiles.py).

    Sert à distinguer une mesure réellement notable d'une mesure dont le niveau est
    sa normale : main.sorted_gaps est TRÈS RARE pour tout tirage, main.sum n'est
    jamais COURANTE. Sans ce profil, le garde lexical compare les mots au maximum de
    rareté de l'ensemble des faits — maximum qui vaut toujours VERY_RARE à cause de
    sorted_gaps, ce qui le rendait incapable de se déclencher.
    """
    path = ROOT / "dist" / "data" / "rarity_profiles.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))["metrics"]


RARITY_PROFILES = load_rarity_profiles()


def notable_level(fact):
    """Niveau de rareté d'un fait S'IL dépasse la référence de sa propre mesure,
    sinon None (le fait est dans sa normale, il n'est pas notable)."""
    prof = RARITY_PROFILES.get(fact.get("metric"))
    if not prof or "rarity" not in fact or prof["constant"]:
        return None
    lvl, base = RARITY_ORDER[fact["rarity"]], RARITY_ORDER[prof["baseline"]]
    return lvl if lvl > base else None

# familles de mesures emboîtées : la mesure fine est un raffinement des mesures
# agrégées de sa famille, donc légitimement plus rare — ce n'est pas une
# contradiction, mais l'article doit le dire explicitement.
METRIC_FAMILIES = [
    ("répartition par dizaines", "main.decade_counts",
     ["main.max_same_decade", "main.occupied_decades"]),
    ("écarts entre numéros", "main.sorted_gaps",
     ["main.span", "main.mean_gap", "main.min_gap", "main.max_gap"]),
]

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
                prof = RARITY_PROFILES.get(f["metric"])
                if prof and prof["constant"]:
                    bits.append(f"ATTENTION rareté NON INFORMATIVE : cette mesure vaut "
                                f"« {RARITY_FR.get(prof['baseline'], prof['baseline'])} » "
                                f"pour TOUT tirage possible — ne la présente jamais comme "
                                f"remarquable")
                elif prof and notable_level(f) is None:
                    bits.append(f"dans sa normale (niveau de référence de cette mesure : "
                                f"« {RARITY_FR.get(prof['baseline'], prof['baseline'])} ») "
                                f"— PAS notable")
                elif prof:
                    bits.append(f"AU-DESSUS de sa référence "
                                f"« {RARITY_FR.get(prof['baseline'], prof['baseline'])} » : "
                                f"seuls {100 * prof['share_above_baseline']:.1f} % des tirages "
                                f"y parviennent — c'est ici que se trouve l'information")
            name, definition = METRIC_DICT.get(f["metric"], ("", ""))
            if name:
                bits.append(f'nom officiel="{name}"')
            if definition:
                bits.append(f"définition : {definition}")
            lines.append(" · ".join(bits))
        elif f.get("statement"):
            lines.append(f"{f['fact_id']} — {f['statement']}")
    return "\n".join(lines)


def family_note(facts):
    """Explique au modèle les familles emboîtées présentes, pour qu'une mesure fine
    plus rare qu'une mesure agrégée de la même famille ne passe pas pour une
    contradiction."""
    present = {f.get("metric") for f in facts["facts"]}
    notes = []
    for label, fine, coarse in METRIC_FAMILIES:
        others = [c for c in coarse if c in present]
        if fine in present and others:
            notes.append(
                f"- Famille « {label} » : {fine} décrit la configuration EXACTE, "
                f"{' et '.join(others)} n'en résument qu'un aspect. La mesure exacte est "
                f"plus spécifique, donc normalement plus rare — ce n'est pas une "
                f"contradiction. Si tu cites plusieurs mesures de cette famille avec des "
                f"niveaux de rareté différents, nomme explicitement chaque mesure et dis "
                f"que la mesure exacte est plus fine que les autres."
            )
    return "\n".join(notes)


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
    # Ne comptent que les faits DÉPASSANT la référence de leur propre mesure. Prendre
    # le maximum brut sur tous les faits rendait ce garde inopérant : sorted_gaps est
    # VERY_RARE pour tout tirage, donc le maximum valait toujours 3 et aucune
    # inflation ne pouvait être signalée.
    max_rarity_available = max(
        (lvl for lvl in (notable_level(f) for f in facts["facts"]) if lvl is not None),
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


def warn_redundant_closing(text):
    """Signale un dernier paragraphe qui ne fait que récapituler : tous ses chiffres
    ont déjà été cités plus haut, il n'apporte donc aucun élément neuf."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paras) < 3:
        return []
    nums_last = normalize_numbers(paras[-1])
    if not nums_last:
        return []
    if not (nums_last - normalize_numbers("\n".join(paras[:-1]))):
        return ["dernier paragraphe : tous ses chiffres ont déjà été cités plus haut "
                "(récapitulatif sans élément neuf — à raccourcir ou à fusionner)"]
    return []


def _sans_accent(s):
    return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()


# Le corps de l'article est affiché par dist/app.js avec textContent, jamais
# innerHTML — choix de sécurité assumé puisque le texte vient d'un LLM. Donc le
# markdown n'est pas interprété : « **Somme** » s'affiche avec ses astérisques.
# On le retire de façon déterministe plutôt que de compter sur l'obéissance du modèle.
MARKDOWN_RE = [
    (re.compile(r"\*\*(.+?)\*\*", re.DOTALL), r"\1"),   # gras **...**
    (re.compile(r"__(.+?)__", re.DOTALL), r"\1"),           # gras __...__
    (re.compile(r"`([^`]+)`"), r"\1"),                      # code `...`
    (re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE), ""),  # titres
    (re.compile(r"^\s{0,3}>\s?", re.MULTILINE), ""),       # citations
    (re.compile(r"^\s{0,3}[-*+]\s+", re.MULTILINE), ""),   # puces
]


def strip_markdown(text):
    for motif, remplacement in MARKDOWN_RE:
        text = motif.sub(remplacement, text)
    return text


def guard_markdown(text):
    """Reste-t-il des marqueurs de mise en forme qui s'afficheraient littéralement ?"""
    return sorted({m for m in ("**", "__", "`") if m in text})


def run_all_guards(text, facts):
    """Les quatre contrôles, en un seul appel, pour pouvoir les rejouer après réparation."""
    word_problems = guard_interpretive_words(text, facts)
    return {
        "mise_en_forme": guard_markdown(text),
        "nombres": sorted(guard_full_text(text, facts)),
        "mots_de_rarete": [w for w, _ in word_problems],
        "noms_de_code": guard_enum_leak(text),
        "effectifs": guard_class_citations(text, facts),
    }


def repair_prompt(text, guards, facts):
    """Renvoie au modèle ses propres violations, avec le motif exact, pour correction
    minimale. Le cas le plus fréquent : un mot de rareté employé sur une mesure qui est
    dans sa normale — souvent parce qu'aucune mesure n'est au-dessus de sa référence,
    et qu'un tirage ordinaire est alors la seule description honnête."""
    notables = [f"{f['fact_id']} ({RARITY_FR.get(f['rarity'], f['rarity'])})"
                for f in facts["facts"] if notable_level(f) is not None]
    etat = ("Mesures réellement AU-DESSUS de leur référence : " + ", ".join(notables)
            if notables else
            "AUCUNE mesure de ce tirage n'est au-dessus de sa référence : sa forme est "
            "ORDINAIRE. C'est une observation valide et suffisante — dis-le simplement, "
            "n'emploie aucun mot de rareté, et ne cherche pas un angle remarquable.")
    violations = []
    if guards["mots_de_rarete"]:
        violations.append("Mots de rareté employés sans justification : "
                          + ", ".join(f'« {w} »' for w in guards["mots_de_rarete"]))
    if guards["nombres"]:
        violations.append("Nombres absents des faits : " + ", ".join(guards["nombres"]))
    if guards["noms_de_code"]:
        violations.append("Noms de code techniques à traduire en français : "
                          + ", ".join(guards["noms_de_code"]))
    if guards["effectifs"]:
        violations.append("Effectifs ou queues erronés : " + " ; ".join(guards["effectifs"]))

    return f"""Ton texte a été refusé par un contrôle automatique. Corrige-le de façon MINIMALE.

{etat}

Violations à corriger :
- """ + "\n- ".join(violations) + f"""

Règles de correction :
- Ne change QUE ce qui est nécessaire pour lever ces violations. Ne réécris pas le reste.
- N'ajoute AUCUN nombre nouveau, ne modifie aucun nombre existant.
- Si un mot de rareté n'est pas justifié, supprime-le ou remplace-le par une formulation neutre qui décrit la mesure sans la qualifier de rare, notable ou exceptionnelle.
- Ne supprime aucun paragraphe entier ; garde la structure.
- Renvoie uniquement le texte corrigé, sans commentaire ni préambule.

TEXTE À CORRIGER :
{text}"""


# Faits sans champ `metric` (probabilité de la grille, signature, historique exact,
# Pascal, règle des étoiles, principe éditorial) : ils étaient ignorés, donc le
# paragraphe citant la probabilité de la combinaison complète n'avait aucun fait
# attribué. On les apparie par un nombre distinctif (au moins 4 chiffres, pour éviter
# qu'un « 2 » attribue n'importe quoi) ou, pour ceux qui n'en contiennent pas, par une
# expression caractéristique de leur énoncé.
NON_METRIC_KEYWORDS = {
    "F.grid.probability": ("probabilite", "combinaison complete"),
    "F.signature": ("forme du tirage", "suite consecutive maximale", "signature"),
    "F.history.exact_main": ("jamais sorti", "quadruplet"),
    "F.pascal.subsets": ("paires", "triplets"),
    "F.stars.rule": ("ancienne regle",),
    "F.editorial.expectation": ("esperance",),
}


def non_metric_evidence(fact, nums, texte):
    grands = {n for n in normalize_numbers(json.dumps(fact, ensure_ascii=False))
              if "." not in n and len(n) >= 4}
    if grands & nums:
        return True
    return any(kw in texte for kw in NON_METRIC_KEYWORDS.get(fact["fact_id"], ()))


def paragraph_evidence(paragraph, facts):
    """Faits effectivement cités dans ce paragraphe, par appariement déterministe.

    Deux voies seulement, pour éviter une attribution qui désigne tout et donc rien :
      - l'effectif de classe du fait apparaît (un nombre distinctif, ex. 141) ;
      - la valeur du fait ET le nom de la mesure apparaissent (ex. « étendue » + 15).
    Le domaine (2 118 760) est exclu : commun à tous les faits, il ne distingue rien.
    Une valeur seule ne suffit pas non plus : « 2 » ou « 4 » se retrouve partout.
    """
    nums = normalize_numbers(paragraph)
    texte = _sans_accent(paragraph)
    used = []
    for f in facts["facts"]:
        if f.get("metric") is None:
            if non_metric_evidence(f, nums, texte):
                used.append(f["fact_id"])
            continue
        effectif = "class_size" in f and normalize_numbers(str(f["class_size"])) & nums
        valeur = "value" in f and not isinstance(f["value"], dict) and \
            bool(normalize_numbers(str(f["value"])) & nums)
        noms = [f.get("label", ""), METRIC_DICT.get(f["metric"], ("", ""))[0]]
        nom = any(len(n) > 3 and _sans_accent(n) in texte for n in noms if n)
        if effectif or (valeur and nom):
            used.append(f["fact_id"])
    return used


def notable_badges(facts):
    """Puces de rareté à afficher, calculées DÉTERMINISTEMENT — jamais rédigées par le
    modèle. Une puce uniquement pour une mesure au-dessus de sa propre référence : un
    badge sur une mesure dans sa normale serait décoratif et trompeur (les écarts
    ordonnés sont « très rares » pour tout tirage possible, la répartition par dizaines
    pour 98 % d'entre eux). Sur les 486 tirages ordinaires, la liste est vide, et c'est
    le comportement attendu.
    """
    badges = []
    for f in facts["facts"]:
        if notable_level(f) is None:
            continue
        prof = RARITY_PROFILES[f["metric"]]
        nom = METRIC_DICT.get(f["metric"], (f.get("label", f["metric"]), ""))[0] \
            or f.get("label", f["metric"])
        badges.append({
            "fact_id": f["fact_id"], "metric": f["metric"], "nom": nom,
            "valeur": f["value"],
            "niveau": f["rarity"],                        # classe CSS .chip.<niveau>
            "libelle": RARITY_FR.get(f["rarity"], f["rarity"]),
            "reference": prof["baseline"],
            "part_au_dessus": prof["share_above_baseline"],
        })
    # la mesure la plus rare d'abord, puis la plus discriminante
    badges.sort(key=lambda b: (-RARITY_ORDER[b["niveau"]], b["part_au_dessus"]))
    # pas deux puces pour la même information : span et mean_gap ont la même classe,
    # on garde la première rencontrée (donc la mieux classée par le tri ci-dessus).
    vus, uniques = set(), []
    for b in badges:
        doublon = any(b["metric"] == autre and a in vus or b["metric"] == a and autre in vus
                      for a, autre, _ in DERIVED_EQUIVALENTS)
        if doublon:
            continue
        vus.add(b["metric"])
        uniques.append(b)
    # au-delà de cinq, la ligne de puces cesse d'être lisible et redevient un inventaire
    return uniques[:5]


def build_compose_article(facts_path, facts, text, guards):
    """Brouillon au schéma aleaquant-article-v1, identique à celui du mode template,
    pour que show / approve / reject et scripts/import_article.py fonctionnent sans
    modification. Le garde enregistré est celui du mode compose (quatre contrôles sur
    le texte entier), pas le garde par claim du mode template."""
    from hashlib import sha256
    import datetime as dt
    from draw_report import digest

    facts_bytes = facts_path.read_bytes()
    paragraphs = [q.strip() for q in text.split("\n\n") if q.strip()]
    claims = [{"claim_id": "C%d" % (i + 1), "text": q, "evidence_ids": paragraph_evidence(q, facts)}
              for i, q in enumerate(paragraphs)]
    used = sorted({i for c in claims for i in c["evidence_ids"]})
    research_pack = {
        "question": "Que dit la forme du tirage %s, sans prétendre prédire le suivant ?" % facts["draw_id"],
        "draw_id": facts["draw_id"], "facts_schema": facts["schema"],
        "facts_sha256": sha256(facts_bytes).hexdigest(), "engine": facts["engine"],
        # le modèle a reçu TOUS les faits : l'evidence du pack les liste tous, et
        # claims[].evidence_ids précise ceux réellement cités par paragraphe.
        "evidence": [{"evidence_id": f["fact_id"], "claim": f.get("statement", ""),
                      "method": f.get("method", ""), "category": f.get("category", ""),
                      "cited": f["fact_id"] in used} for f in facts["facts"]],
    }
    problems = []
    for nom, liste in guards.items():
        problems += [f"{nom}: {x}" for x in liste]
    body = text.strip() + "\n\n" + METHODO_NOTE
    d = {"title": "EuroMillions — tirage du %s" % date_fr(facts["date"]), "body": body,
         "claims": claims, "badges": notable_badges(facts), "writer": COMPOSE_WRITER,
         "research_pack_sha256": digest(research_pack)}
    return {"schema": "aleaquant-article-v1", "article_id": "tirage-" + facts["draw_id"],
            "kind": "draw_report", "status": "PENDING_HUMAN" if not problems else "BLOCKED",
            "guard": {"problems": problems, "mode": "compose", "checks": guards},
            "draft_sha256": digest(d), "draft": d, "research_pack": research_pack,
            "human_decision": None,
            "provenance": {"writer": COMPOSE_WRITER, "model": MODEL,
                           "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                           "facts_path": str(facts_path)}}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("draw_id")
    ap.add_argument("--write", action="store_true",
                    help="écrit le brouillon dans runs-llm-compose/<id>/draft.json")
    ap.add_argument("--text-file", type=Path,
                    help="construit le brouillon depuis un texte existant, sans appel API")
    ap.add_argument("--no-repair", action="store_true",
                    help="n'essaie pas de faire corriger une violation par le modèle")
    args = ap.parse_args()
    draw_id = args.draw_id
    facts_path = ROOT / "dist" / "data" / "facts" / f"{draw_id}.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))

    main_nums = ' · '.join('%02d' % n for n in facts['main'])
    stars = ' · '.join('%02d' % n for n in facts['stars'])
    redundancy = redundancy_note(facts)
    redundancy_section = f"\nMétriques redondantes à ne pas double-compter :\n{redundancy}\n" if redundancy else ""
    families = family_note(facts)
    family_section = f"\nFamilles de mesures emboîtées :\n{families}\n" if families else ""

    prompt = f"""Tu es rédacteur scientifique pour AleaQuant, un site français de vulgarisation sur les probabilités et la combinatoire appliquées à EuroMillions. Ta ligne éditoriale : rigueur, jamais de prédiction, jamais de promesse de gain, chaque nombre cité doit venir des faits fournis ci-dessous.

Tirage du {date_fr(facts['date'])} : {main_nums} ★ {stars}

Faits calculés disponibles (utilise ceux qui sont pertinents, pas besoin de tous les citer) :
{evidence_block(facts)}
{redundancy_section}{family_section}
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
k. N'écris PAS de paragraphe de synthèse qui récapitule ce que tu viens de dire : chaque paragraphe doit apporter un constat neuf. Si tu n'as plus rien à ajouter, termine sur ton dernier constat.
l. Emploie le nom officiel fourni pour chaque mesure (champ nom officiel=) plutôt qu'une formulation de ton invention, et donne en quelques mots la définition fournie la première fois qu'un terme n'est pas évident pour un lecteur non initié (par exemple "paires de mêmes unités : deux numéros se terminant par le même chiffre").
m. Ne balaie pas toutes les mesures disponibles : choisis-en au plus sept, celles qui servent ton angle. Écarte les mesures secondaires de niveau courant qui n'apportent rien au propos plutôt que de les énumérer.
n. N'emploie un mot de rareté QUE pour une mesure marquée « AU-DESSUS de sa référence ». Une mesure « dans sa normale » ou « NON INFORMATIVE » se cite sans aucun qualificatif de rareté : son niveau est celui de presque tous les tirages, le signaler comme remarquable serait trompeur.
o. Pour expliquer ce que mesure une grandeur, reprends la définition officielle fournie plutôt qu'une paraphrase de ton cru (l'étendue est « l'écart entre le plus petit et le plus grand numéro », pas « le sommet de 35 à 50 »).
p. Écris en TEXTE BRUT. Aucun markdown : pas d'astérisques pour le gras, pas de titres, pas de puces, pas d'accents graves. La page affiche ton texte tel quel, donc un « ** » s'y verrait littéralement. Pour mettre en valeur un terme, emploie les mots, pas la typographie.
q. Varie ta structure et tes formulations d'un article à l'autre, n'utilise pas un patron figé. Style vivant mais rigoureux, pas de sensationnalisme."""

    if args.text_file:
        text = strip_markdown(args.text_file.read_text(encoding="utf-8")).strip()
        # un corps d'article déjà produit contient la note de méthode en dernier
        # paragraphe : on la retire pour ne pas la dupliquer à la reconstruction.
        if text.endswith(METHODO_NOTE):
            text = text[: -len(METHODO_NOTE)].strip()
        resp, proof = None, None
    else:
        from openai import OpenAI
        client = OpenAI(api_key=load_key())
        resp = client.responses.create(model=MODEL, input=prompt, reasoning={"effort": "low"})
        text = resp.output_text

    # --- passe de relecture : langue seulement, jamais les chiffres ni les raretés ---
    proof_prompt = f"""Corrige uniquement l'orthographe, la grammaire et les accords du texte ci-dessous (français).

INTERDICTIONS ABSOLUES : ne modifie, n'ajoute ni ne supprime aucun chiffre, aucun pourcentage, aucun identifiant technique, aucun mot de rareté (courant, peu courant, rare, très rare). Ne reformule pas, ne raccourcis pas, ne réorganise pas les paragraphes. Renvoie uniquement le texte corrigé, sans commentaire ni préambule.

TEXTE :
{text}"""
    if args.text_file:
        proofed, proof_status = text, "non lancée (texte fourni)"
        proof = None
    else:
        proof = client.responses.create(model=MODEL, input=proof_prompt, reasoning={"effort": "low"})
        proofed = proof.output_text.strip()

    # contrôle déterministe : la relecture ne doit avoir touché ni les nombres ni les
    # mots de rareté. Sinon on garde le texte d'origine.
    same_numbers = normalize_numbers(proofed) == normalize_numbers(text)
    same_rarity = sorted(w for w, _ in guard_interpretive_words(proofed, {"facts": []})) == \
        sorted(w for w, _ in guard_interpretive_words(text, {"facts": []}))
    if args.text_file:
        final_text = text
    elif same_numbers and same_rarity:
        final_text = proofed
        proof_status = "appliquée"
    else:
        final_text = text
        proof_status = f"REJETÉE (nombres identiques={same_numbers}, raretés identiques={same_rarity})"

    text = strip_markdown(final_text).strip()

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

    md = guard_markdown(text)
    print("\n=== GARDE MISE EN FORME (marqueurs markdown résiduels) ===")
    print("OK" if not md else f"MARQUEURS RESTANTS : {md}")

    cite_problems = guard_class_citations(text, facts)
    print("\n=== GARDE EFFECTIFS (classes et queues citées vs faits sources) ===")
    print("OK" if not cite_problems else "ÉCARTS :\n  - " + "\n  - ".join(cite_problems))

    warns = warn_global_qualifiers(text) + warn_redundant_closing(text)
    print("\n=== AVERTISSEMENTS ÉDITORIAUX (à relire, non bloquants) ===")
    print("aucun" if not warns else "\n  - ".join([""] + warns).strip())

    appels = [r for r in (resp, proof) if r is not None]
    in_tok = sum((getattr(r.usage, "input_tokens", 0) or 0) for r in appels)
    out_tok = sum((getattr(r.usage, "output_tokens", 0) or 0) for r in appels)
    cost = in_tok / 1e6 * 0.75 + out_tok / 1e6 * 4.50
    print(f"\n=== COÛT === {cost:.5f} $ (in={in_tok} out={out_tok})")

    guards = {"nombres": sorted(problems), "mots_de_rarete": [w for w, _ in word_problems],
              "noms_de_code": leaks, "effectifs": cite_problems, "mise_en_forme": md}

    # --- réparation : on renvoie au modèle sa violation et on rejoue les gardes ---
    if any(guards.values()) and not args.text_file and not args.no_repair:
        print("\n=== RÉPARATION === contrôle en échec, nouvelle tentative")
        fix = client.responses.create(model=MODEL, input=repair_prompt(text, guards, facts),
                                      reasoning={"effort": "low"})
        repaired = fix.output_text.strip()
        new_guards = run_all_guards(repaired, facts)
        # la réparation ne doit pas introduire de nombre nouveau
        sans_nouveau_nombre = not (normalize_numbers(repaired) - normalize_numbers(text))
        if not any(new_guards.values()) and sans_nouveau_nombre:
            text, guards = repaired, new_guards
            print("réparation ACCEPTÉE : tous les contrôles passent")
        else:
            motif = ("nombre nouveau introduit" if not sans_nouveau_nombre
                     else f"contrôles encore en échec : { {k: v for k, v in new_guards.items() if v} }")
            print(f"réparation REFUSÉE ({motif}) — le texte d'origine est conservé")
        cost += ((getattr(fix.usage, "input_tokens", 0) or 0) / 1e6 * 0.75
                 + (getattr(fix.usage, "output_tokens", 0) or 0) / 1e6 * 4.50)
        print(f"coût cumulé : {cost:.5f} $")
        print("\n=== TEXTE RETENU ===\n")
        print(text)

    if args.write:
        article = build_compose_article(facts_path, facts, text, guards)
        out = ROOT / "runs-llm-compose" / draw_id / "draft.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n=== BROUILLON ÉCRIT === {out}")
        print(f"statut : {article['status']} · {len(article['draft']['claims'])} paragraphes · "
              f"{len([c for c in article['draft']['claims'] if c['evidence_ids']])} avec faits cités")
        b = article["draft"]["badges"]
        print("puces : " + (", ".join(f"{x['nom']} = {x['valeur']} ({x['libelle']})" for x in b)
                            if b else "aucune (aucune mesure au-dessus de sa référence)"))
        print(f"relecture humaine : python3 agent/draw_report.py show {out}")


if __name__ == "__main__":
    main()
