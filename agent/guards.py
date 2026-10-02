"""Préparation des faits, gardes déterministes et construction du brouillon.

Version : 0.9 · Date : 2026-10-02 · Auteur : AleaQuant
Historique : 0.9 reconnaît aussi « sous-total » au singulier dans les sommes par dizaine.
Historique : 0.8 ajoute la traçabilité partagée et supprime les appariements numériques seuls.
Historique : expose le profil de sommes par dizaine sans le classer en rareté.
TODO : étendre le contrôle à tous les exports hérités avant publication.

Module SANS appel réseau ni LLM : tout ici est déterministe et testable hors ligne.
Extrait de compose_draw_report.py pour être la brique commune aux deux chaînes
éditoriales — le pipeline LangGraph d'aleaquant-editorial-agents doit l'IMPORTER, pas
le recopier : une copie divergerait, comme le prompt l'a fait avant son extraction.

Ce que ce module porte, et pourquoi chaque pièce existe : voir docs/GARDES.md. Les
tests de tests/test_guards.py encodent chacun un échec réel constaté en production —
ils sont la mémoire de ce qui a été appris, à ne pas assouplir sans lire le document.

Trois couches :
  1. préparation des faits — evidence_block(), family_note(), redundancy_note() :
     annote chaque fait de son niveau de rareté ET de sa position par rapport à la
     référence de sa propre mesure, déclare les familles emboîtées et les métriques
     redondantes ;
  2. gardes — six contrôles déterministes sur le texte produit (nombres, mots de
     rareté, noms de code, effectifs de classe, mise en forme, vocabulaire) plus deux
     avertissements éditoriaux, et repair_prompt() pour faire corriger une violation ;
  3. sortie — paragraph_evidence(), notable_badges(), build_compose_article() :
     appariement paragraphe/fait, puces de rareté, brouillon au schéma
     aleaquant-article-v1.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "tools"))
from draw_report import normalize_numbers, pct, date_fr  # noqa: E402,F401
from lint_language import lint as lint_language  # noqa: E402


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
            value = f['value']
            if isinstance(value, dict) and isinstance(value.get('profile'), list):
                value = ' ; '.join(
                    f"D{b['decade']} : {b['count']} "
                    f"{'numéro' if b['count'] == 1 else 'numéros'}, somme {b['sum']}"
                    for b in value['profile'])
            bits = [f"{f['fact_id']} — {f.get('label', f['metric'])} : {value}"]
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
                    bits.append("Consigne interne : qualificatif du champ rareté autorisé pour cette mesure. "
                                "Ne pas commenter le seuil éditorial ni comparer la valeur à un libellé de classe.")
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
DECADE_NARRATIVE_RANGE_RE = re.compile(
    r'\b(?:1\s*[-–—]\s*10|11\s*[-–—]\s*20|21\s*[-–—]\s*30|'
    r'31\s*[-–—]\s*40|41\s*[-–—]\s*(?:49|50))\b'
)


def guard_decade_ranges(text):
    """Les articles nomment les décades par rang, sans énumérer leurs bornes."""
    return [m.group(0) for m in DECADE_NARRATIVE_RANGE_RE.finditer(text)]


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
    return unicodedata.normalize("NFD", s.lower().replace("’", "'")).encode("ascii", "ignore").decode()


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


def run_all_guards(text, facts, editorial_style=False):
    """Contrôles partagés ; la règle de style sur les décades reste hors du batch."""
    from article_traceability import interpretation_issues, scoped_rarity_issues
    word_problems = guard_interpretive_words(text, facts)
    return {
        "interpretation": interpretation_issues(text) + scoped_rarity_issues(text, facts),
        "vocabulaire": [f"{nom} — {extrait}" for nom, extrait, _ in lint_language(text)],
        **({"plages_de_decades": guard_decade_ranges(text)} if editorial_style else {}),
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
    if guards.get("vocabulaire"):
        violations.append("Formulations interdites par la ligne éditoriale (jamais de "
                          "prédiction, de promesse de gain ni de comparaison de grilles) : "
                          + " ; ".join(guards["vocabulaire"]))
    if guards.get("mise_en_forme"):
        violations.append("Marqueurs de mise en forme à retirer : "
                          + ", ".join(guards["mise_en_forme"]))
    if guards.get("interpretation"):
        violations.append("Retirer la comparaison au seuil éditorial : " + "; ".join(guards["interpretation"]))
    if guards.get("plages_de_decades"):
        violations.append("Plages de décades à remplacer par leur rang : "
                          + ", ".join(guards["plages_de_decades"]))

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
    "F.grid.probability": ("probabilite",),
    "F.signature": ("forme du tirage", "signature"),
    "F.history.exact_main": ("jamais sorti", "quadruplet"),
    "F.pascal.subsets": ("paires", "triplets"),
    "F.stars.rule": ("ancienne regle",),
    "F.editorial.expectation": ("esperance",),
}


def non_metric_evidence(fact, nums, texte):
    if fact['fact_id'] == 'F.grid.probability':
        value = fact.get('value', {})
        domains = [value.get('main_domain'), value.get('stars_domain')] if isinstance(value, dict) else []
        if any(d and re.search(r"\b1\s*(?:a|[-–])\s*" + str(d) + r"\b", texte) for d in domains):
            return True  # le fait de règle justifie aussi le domaine de numéros
    return any(kw in texte for kw in NON_METRIC_KEYWORDS.get(fact["fact_id"], ()))


# Noms métier et paraphrases usuelles. Un effectif seul n'identifie jamais une
# métrique : « 3 » peut désigner une décade, un écart ou une classe d'étoiles.
METRIC_ALIASES = {
    "main.decade_counts": ("repartition par dizaines", "repartition par decades", "decade 1", "decade 2", "decade 3", "decade 4", "decade 5"),
    "main.occupied_decades": ("dizaines occupees", "decades occupees", "4 dizaines", "quatre dizaines", "2 dizaines", "deux dizaines", "3 dizaines", "trois dizaines"),
    "main.max_same_decade": ("meme dizaine", "meme decade"),
    "main.longest_consecutive_run": ("suite consecutive maximale", "suite maximale", "plus longue suite"),
    "main.decade_sums": ("sommes par dizaine", "somme par dizaine", "sous-totaux", "sous-total", "sommes par decade"),
    "stars.gap": ("ecart des etoiles", "ecart entre les etoiles"),
}


def paragraph_evidence(paragraph, facts):
    """Rattachement lexical conservateur par mesure et composante, jamais par nombre seul.

    Ce détecteur aide la review ; il ne certifie pas toutes les paraphrases possibles.
    Les nouvelles métriques utilisent automatiquement leur libellé et le dictionnaire.
    """
    texte = _sans_accent(paragraph)
    sentences = re.split(r"[.!?;]\s+", texte)
    used = []
    for f in facts["facts"]:
        metric = f.get("metric")
        if metric is None:
            if non_metric_evidence(f, set(), texte):
                used.append(f["fact_id"])
            continue
        names = [f.get("label", ""), METRIC_DICT.get(metric, ("", ""))[0]]
        aliases = [_sans_accent(n) for n in names if len(n) > 3]
        aliases += list(METRIC_ALIASES.get(metric, ()))
        for sentence in sentences:
            star = "etoile" in sentence
            if metric.startswith('stars.'):
                if not star:
                    continue
                if metric == 'stars.sum':
                    aliases = ['somme']
                elif metric == 'stars.gap':
                    aliases = ['ecart']
            elif metric.startswith('main.') and star and not any(w in sentence for w in ('numero', 'principa')):
                continue
            if any(re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", sentence) for n in aliases):
                used.append(f['fact_id'])
                break
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


def build_compose_article(facts_path, facts, text, guards, angle=None, *, mode="direct", model=None, generation=None):
    """Brouillon au schéma aleaquant-article-v1, identique à celui du mode template,
    pour que show / approve / reject et scripts/import_article.py fonctionnent sans
    modification. Le garde enregistré est celui du mode compose (quatre contrôles sur
    le texte entier), pas le garde par claim du mode template."""
    from hashlib import sha256
    import datetime as dt
    from draw_report import digest

    from article_traceability import build_methodology, validate_traceability
    facts_bytes = facts_path.read_bytes()
    if json.loads(facts_bytes) != facts:
        raise ValueError("Les faits en mémoire diffèrent du fichier source")
    model = model or MODEL
    writer = f"aleaquant-draw-report-compose-v1-{model}" + ("-batch" if mode == "batch" else "")
    guards = run_all_guards(text, facts, editorial_style=bool(angle))
    paragraphs = [q.strip() for q in text.split("\n\n") if q.strip()]
    claims = [{"claim_id": "C%d" % (i + 1), "text": q, "evidence_ids": paragraph_evidence(q, facts)}
              for i, q in enumerate(paragraphs) if paragraph_evidence(q, facts) or re.search(r"\d", q)]
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
    body = text.strip()
    game_names = {"euromillions": "EuroMillions", "loto": "Loto", "keno": "Keno"}
    game_name = game_names.get(facts.get("game_id"), facts.get("game_id", "Jeu").replace("_", " ").title())
    draw_title = "%s — tirage du %s" % (game_name, date_fr(facts["date"]))
    # Le hook éditorial reste libre, mais le titre final identifie toujours le jeu
    # et la date. Cette information ne dépend donc pas du rappel du modèle.
    final_title = "%s : %s" % (draw_title, angle["title"]) if angle else draw_title
    d = {"title": final_title, "body": body,
         "claims": claims, "badges": notable_badges(facts), "writer": writer,
         "methodology": build_methodology(facts, claims),
         "research_pack_sha256": digest(research_pack)}
    if angle:
        d["editorial_angle"] = angle
    article = {"schema": "aleaquant-article-v1", "article_id": "tirage-" + facts["draw_id"],
            "kind": "draw_report", "status": "PENDING_HUMAN" if not problems else "BLOCKED",
            "guard": {"problems": problems, "mode": "compose", "checks": guards},
            "draft_sha256": digest(d), "draft": d, "research_pack": research_pack,
            "human_decision": None,
            "provenance": {"writer": writer, "model": model, "mode": mode,
                           "traceability_version": "traceability-v1",
                           **(generation or {}),
                           "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                           "facts_path": str(facts_path)}}

    issues = validate_traceability(article, facts)
    article['guard']['checks']['traceability'] = issues
    article['guard']['problems'] = list(dict.fromkeys(problems + issues))
    article['status'] = 'BLOCKED' if article['guard']['problems'] else 'PENDING_HUMAN'
    return article
