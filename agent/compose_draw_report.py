"""Rapport de tirage — chaîne de production (mode « compose »).

Auteur : AleaQuant · 2026-10-02 · Révision traçabilité : note publique, preuves et SHA de la version relue.

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

Version : 0.8 · Date : 2026-10-02 · Auteur : AleaQuant
Historique : charge la constitution SEO Writer partagée avec LangGraph ; TODO : aligner
les métadonnées et la structure HTML du site sur le contrat éditorial publié.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT.parent / "aleaquant-editorial-agents" / ".env"
SEO_WRITER_RULES_PATH = ROOT.parent / "aleaquant-editorial-agents" / "constitution" / "seo-editorial.md"

sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "tools"))
from draw_report import normalize_numbers, pct, date_fr  # noqa: E402
from lint_language import lint as lint_language  # noqa: E402

# même mapping que dist/draws.js (RARITY) — le modèle ne doit voir que le français
# Préparation des faits, gardes et construction du brouillon : agent/guards.py.
# Ce module-ci ne porte que le prompt de composition et le CLI.
from guards import (  # noqa: E402
    COMPOSE_WRITER, METHODO_NOTE, MODEL, RARITY_FR, build_compose_article,
    evidence_block, family_note, guard_class_citations, guard_decade_ranges, guard_enum_leak,
    guard_full_text, guard_interpretive_words, guard_markdown, lint_language,
    load_key, notable_badges, notable_level, redundancy_note, repair_prompt, run_all_guards,
    strip_markdown, warn_global_qualifiers, warn_redundant_closing,
)


def compose_prompt(facts, angle=None):
    """Prompt de base partagé avec le batch ; variantes expérimentales seulement avec angle."""
    if not SEO_WRITER_RULES_PATH.is_file():
        raise FileNotFoundError(f"Consignes SEO partagées introuvables : {SEO_WRITER_RULES_PATH}")
    seo_writer_rules = SEO_WRITER_RULES_PATH.read_text(encoding="utf-8").strip()
    traceability_rules = (SEO_WRITER_RULES_PATH.parent / "traceability.md").read_text(encoding="utf-8")
    seo_writer_rules += "\n\n" + traceability_rules
    main_nums = ' · '.join('%02d' % n for n in facts['main'])
    stars = ' · '.join('%02d' % n for n in facts['stars'])
    redundancy = redundancy_note(facts)
    redundancy_section = f"\nMétriques redondantes à ne pas double-compter :\n{redundancy}\n" if redundancy else ""
    families = family_note(facts)
    family_section = f"\nFamilles de mesures emboîtées :\n{families}\n" if families else ""
    angle_section = ""
    if angle:
        angle_section = ("\nAngle choisi par la rédaction avant l'article :\n"
                         f"Titre : {angle['title']}\n"
                         f"Chemin de lecture : {angle['angle']}\n"
                         f"Faits d'appui : {', '.join(angle['evidence_ids'])}\n"
                         "Développe cet angle dans le corps sans recopier le titre ; "
                         "ne laisse pas l'angle effacer les autres constats nécessaires.\n")
    opening_rule = (
        "1. Ouvre sur le fait concret qui porte l'angle choisi, puis situe le résultat "
        "et sa date. Intègre la probabilité de la combinaison exacte dans ce passage "
        "ou le suivant, sans préambule générique sur toutes les grilles."
        if angle else "1. Situe le tirage (probabilité de la combinaison exacte)."
    )
    geometry_rule = (
        "2. Commente la GÉOMÉTRIE du tirage : les numéros sont-ils plutôt concentrés "
        "(proches les uns des autres, dans peu de décades) ou dispersés sur l'étendue 1-50 ? "
        "Nomme les décades par leur rang (décade 1, décade 2, etc.), jamais par leurs "
        "bornes numériques. La numérotation commence à 1 pour les dix premiers numéros. "
        "Tu peux compléter les effectifs par les sous-totaux des numéros de chaque dizaine, "
        "mais ceux-ci sont descriptifs et n'ont pas de rareté attribuée. "
        "Attention au SENS de la mesure : une étendue élevée (proche de 49) signifie "
        "dispersé, une étendue faible signifie concentré — ne qualifie jamais une "
        "grande étendue de \"resserrée\" ni l'inverse."
        if angle else
        '2. Commente la GÉOMÉTRIE du tirage : les numéros sont-ils plutôt concentrés '
        '(proches les uns des autres, dans peu de dizaines) ou dispersés sur l\'étendue '
        '1-50 ? Nomme les tranches par leur rang (décade 1, décade 2, etc.), jamais par '
        'leurs bornes numériques. Tu peux compléter les effectifs par les sous-totaux des '
        'numéros de chaque dizaine, mais ceux-ci sont descriptifs et n’ont pas de rareté attribuée. '
        'Attention au SENS de la mesure : une étendue élevée (proche de 49) signifie '
        'dispersé, une étendue faible signifie concentré — ne qualifie jamais une '
        'grande étendue de "resserrée" ni l\'inverse.'
    )
    style_rule = (
        "\nr. Écris des paragraphes reliés par une progression d'idées : une observation "
        "ouvre une question, la mesure y répond, puis l'historique ajoute un autre point "
        "de vue. Privilégie les phrases naturelles et varie leur longueur. Évite "
        "l'inventaire de métriques et les transitions mécaniques du type « Côté... » "
        "ou « Enfin... »."
        if angle else ""
    )

    prompt = f"""Tu es rédacteur scientifique pour AleaQuant, un site français de vulgarisation sur les probabilités et la combinatoire appliquées à EuroMillions. Ta ligne éditoriale : rigueur, jamais de prédiction, jamais de promesse de gain, chaque nombre cité doit venir des faits fournis ci-dessous.

Consignes SEO versionnées communes au Writer LangGraph :
{seo_writer_rules}

Tirage du {date_fr(facts['date'])} : {main_nums} ★ {stars}

Faits calculés disponibles (utilise ceux qui sont pertinents, pas besoin de tous les citer) :
{evidence_block(facts)}
{redundancy_section}{family_section}{angle_section}
Écris un article de 4 à 6 paragraphes qui :
{opening_rule}
{geometry_rule}
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
n. N'emploie un mot de rareté QUE lorsque la consigne interne du fait autorise son qualificatif. Ne compare jamais une valeur à un libellé tel que « classe peu courante » ; ne recopie pas les seuils de sélection éditoriaux dans le texte. Une mesure « dans sa normale » ou « NON INFORMATIVE » se cite sans aucun qualificatif de rareté : son niveau est celui de presque tous les tirages, le signaler comme remarquable serait trompeur.
o. Pour expliquer ce que mesure une grandeur, reprends la définition officielle fournie plutôt qu'une paraphrase de ton cru (l'étendue est « l'écart entre le plus petit et le plus grand numéro », pas « le sommet de 35 à 50 »).
p. Écris en TEXTE BRUT. Aucun markdown : pas d'astérisques pour le gras, pas de titres, pas de puces, pas d'accents graves. La page affiche ton texte tel quel, donc un « ** » s'y verrait littéralement. Pour mettre en valeur un terme, emploie les mots, pas la typographie.
q. Varie ta structure et tes formulations d'un article à l'autre, n'utilise pas un patron figé. Style vivant mais rigoureux, pas de sensationnalisme.{style_rule}"""
    return prompt


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("draw_id")
    ap.add_argument("--write", action="store_true",
                    help="écrit le brouillon dans runs-llm-compose/<id>/draft.json")
    ap.add_argument("--out", type=Path, help="nouveau brouillon témoin, sans écraser la review")
    ap.add_argument("--text-file", type=Path,
                    help="construit le brouillon depuis un texte existant, sans appel API")
    ap.add_argument("--no-repair", action="store_true",
                    help="n'essaie pas de faire corriger une violation par le modèle")
    ap.add_argument("--angle", type=Path,
                    help="sélection A/B/C issue de editorial_angle.py (selected.json)")
    args = ap.parse_args()
    draw_id = args.draw_id
    facts_path = ROOT / "dist" / "data" / "facts" / f"{draw_id}.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    if args.angle:
        from editorial_angle import load_selected
        angle = load_selected(args.angle, facts)
    else:
        angle = None

    prompt = compose_prompt(facts, angle)

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

    decade_ranges = guard_decade_ranges(text) if angle else []
    print("\n=== GARDE DÉCADES (rang plutôt que plages numériques) ===")
    print("OK" if not decade_ranges else f"PLAGES À REMPLACER : {decade_ranges}")

    md = guard_markdown(text)
    print("\n=== GARDE MISE EN FORME (marqueurs markdown résiduels) ===")
    print("OK" if not md else f"MARQUEURS RESTANTS : {md}")

    vocab = lint_language(text)
    print("\n=== GARDE VOCABULAIRE (formulations prédictives, D3) ===")
    if not vocab:
        print("OK")
    else:
        for nom, extrait, conseil in vocab:
            print(f"  [{nom}] {extrait}")
            print(f"      → {conseil}")

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
              "noms_de_code": leaks, "plages_de_decades": decade_ranges,
              "effectifs": cite_problems, "mise_en_forme": md,
              "vocabulaire": [f"{nom} — {extrait}" for nom, extrait, _ in vocab]}

    guards = run_all_guards(text, facts, editorial_style=bool(angle))

    # --- réparation : on renvoie au modèle sa violation et on rejoue les gardes ---
    if any(guards.values()) and not args.text_file and not args.no_repair:
        print("\n=== RÉPARATION === contrôle en échec, nouvelle tentative")
        fix = client.responses.create(model=MODEL, input=repair_prompt(text, guards, facts),
                                      reasoning={"effort": "low"})
        repaired = fix.output_text.strip()
        new_guards = run_all_guards(repaired, facts, editorial_style=bool(angle))
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
        from hashlib import sha256
        article = build_compose_article(facts_path, facts, text, guards, angle=angle,
            mode="text_import" if args.text_file else "direct",
            generation={"prompt_sha256": sha256(prompt.encode()).hexdigest(), "reasoning_effort": "low"})
        out = args.out or ROOT / "runs-llm-compose" / draw_id / "draft.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n=== BROUILLON ÉCRIT === {out}")
        print(article["draft"]["methodology"]["note"])
        print(f"statut : {article['status']} · {len(article['draft']['claims'])} paragraphes · "
              f"{len([c for c in article['draft']['claims'] if c['evidence_ids']])} avec faits cités")
        b = article["draft"]["badges"]
        print("puces : " + (", ".join(f"{x['nom']} = {x['valeur']} ({x['libelle']})" for x in b)
                            if b else "aucune (aucune mesure au-dessus de sa référence)"))
        print(f"relecture humaine : python3 agent/draw_report.py show {out}")


if __name__ == "__main__":
    main()
