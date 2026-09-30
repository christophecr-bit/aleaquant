"""Linter de vocabulaire — transforme la ligne éditoriale en test qui échoue.

Chantier D3 de TODO-V0.md. Aucun LLM : des règles explicites, testées, avec pour chacune
un message disant quoi écrire à la place. Le principe de tri : une formulation est
légitime quand elle porte une MESURE et une RÉFÉRENCE ; elle est refusée quand elle
prédit, promet, ou compare des grilles entre elles.

  python3 tools/lint_language.py "texte à vérifier"
  python3 tools/lint_language.py --file article.txt
  python3 tools/lint_language.py --drafts            # tous les brouillons du dépôt
  python3 tools/lint_language.py --self-test         # corpus interdit + corpus légitime

Code de sortie : 0 si rien à signaler, 1 sinon (utilisable en garde-fou).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalise(texte):
    """Minuscules sans accents : les règles s'écrivent une seule fois."""
    return unicodedata.normalize("NFD", texte.lower()).encode("ascii", "ignore").decode()


# Chaque règle : (identifiant, motif, exception, conseil).
# L'exception est cherchée dans la PHRASE qui contient le motif, pas après lui : une
# négation légitime (« aucune de ces mesures ne prédit le prochain tirage ») précède
# souvent la formulation suspecte, donc un lookahead ne peut pas la voir.
REGLES_BRUTES = [
    ("prediction.va_sortir",
     r"\b(va|vont|devrait|devraient|pourrait|pourraient)\s+(bient[o]t\s+)?(sortir|tomber|arriver|revenir)\b",
     None,
     "Aucune mesure ne prédit un tirage. Décrire ce qui a été observé, au passé."),

    ("prediction.prochain_tirage",
     r"\b(au|le|du|pour le)\s+prochain\s+tirage\b",
     r"\b(aucun|aucune|ne\s+(permet|predit|prevoit|dit)|pas\s+de\s+prediction|rien\s+ne|sans\s+predire)\b",
     "Ne rien affirmer sur le prochain tirage, sauf pour rappeler qu'aucune mesure ne le prédit."),

    ("chances.augmentees",
     r"\b(chances?|probabilites?)\s+(augmentees?|accrues?|ameliorees?|meilleures?|plus\s+fortes?)\b"
     r"|\b(meilleures?|plus\s+fortes?|plus\s+grandes?)\s+(chances?|probabilites?)\b",
     r"\bp\s*\(|\bprobabilite\s+d[e']\s*au\s+moins\b|\bcalculee?\b|\bexhaustiv",
     "La probabilité d'une combinaison complète est fixe. Parler de la classe et de son effectif."),

    ("chances.maximiser",
     r"\b(maximiser|augmenter|ameliorer|booster|optimiser)\s+(ses\s+|vos\s+|les\s+)?(chances|gains?|probabilites?)\b",
     None,
     "Aucune sélection ne modifie la probabilité de gagner. Décrire la couverture combinatoire."),

    ("grille.meilleure",
     r"\b(meilleure?s?|bonne?s?|mauvaise?s?|ideale?s?|optimale?s?)\s+(grille|combinaison|numeros?)\b",
     None,
     "Aucune grille n'est meilleure qu'une autre. Comparer des couvertures, pas des mérites."),

    ("grille.gagnante",
     r"\bgrilles?\s+gagnantes?\b",
     r"\bnombre\s+de\b|\battendu\w*\b|\bsur\s+\d|\bloi\b|\besperance\b",
     "« grille gagnante » suggère une recette. Écrire « nombre de grilles gagnantes attendu sur N », avec sa loi."),

    ("numeros.chauds_froids",
     r"\bnumeros?\s+(chauds?|froids?|porte-?bonheurs?|fetiches?)\b",
     None,
     "Notion sans fondement : les tirages sont indépendants sous l'hypothèse du modèle."),

    ("retard.donc",
     r"\b(en\s+retard|pas\s+sorti\s+depuis|absents?\s+depuis)\b[^.]{0,60}\b(donc|il\s+faut|a\s+jouer|revient|devrait)\b",
     None,
     "Un retard n'annonce rien. Le comparer au temps d'attente attendu sous hasard pur."),

    ("promesse.gain",
     r"\b(garantit?|assure|promet|permet)\b[^.]{0,40}\b(de\s+)?(gagner|gain|jackpot)\b",
     r"\besperance\s+de\s+gain\b",
     "Aucune promesse de gain. L'espérance d'une mise est négative."),

    ("promesse.strategie",
     r"\b(strategie|methode|astuce|technique|systeme)\b[^.]{0,30}\b(gagnante?s?|infaillibles?|efficaces?)\b",
     None,
     "Pas de stratégie gagnante. Décrire ce que la combinatoire permet de couvrir."),

    ("esperance.comparaison",
     r"\b(esperance|rendement)\b[^.]{0,50}\b(meilleure?|superieure?|plus\s+elevee?|plus\s+interessante?)\b",
     None,
     "L'espérance d'une mise est identique et négative : elle ne distingue pas deux portefeuilles."),

    ("conseil.jouer",
     r"\b(jouez|misez|privilegiez|evitez\s+de\s+jouer|il\s+faut\s+jouer)\b",
     None,
     "AleaQuant ne conseille aucun jeu. Rester descriptif."),
]

REGLES = [(nom, re.compile(motif), re.compile(exc) if exc else None, conseil)
          for nom, motif, exc, conseil in REGLES_BRUTES]

PHRASE_RE = re.compile(r"[^.!?\n]+")


def lint(texte):
    """Retourne la liste des infractions : (règle, extrait, conseil).

    Chaque motif est cherché phrase par phrase, et l'exception de la règle est évaluée
    sur la phrase entière : c'est le contexte qui distingue « aucune mesure ne prédit le
    prochain tirage » de « à jouer au prochain tirage ».
    """
    norm = normalise(texte)
    trouvees = []
    for phrase_m in PHRASE_RE.finditer(norm):
        phrase = phrase_m.group(0)
        for nom, motif, exception, conseil in REGLES:
            if exception and exception.search(phrase):
                continue
            m = motif.search(phrase)
            if not m:
                continue
            debut = phrase_m.start()
            extrait = texte[debut:phrase_m.end()].replace("\n", " ").strip()
            trouvees.append((nom, extrait, conseil))
    return trouvees


def rapport(titre, texte):
    infractions = lint(texte)
    if not infractions:
        print(f"OK — {titre}")
        return 0
    print(f"REFUSÉ — {titre} ({len(infractions)} infraction(s))")
    for nom, extrait, conseil in infractions:
        print(f"  [{nom}] …{extrait}…")
        print(f"      → {conseil}")
    return 1


# --- corpus de test, écrit à la main : la spécification exécutable du linter ---

INTERDITES = [
    "Le 42 va sortir bientôt, il est en retard donc il faut le jouer.",
    "Cette grille offre de meilleures chances de gagner.",
    "Voici la meilleure combinaison à jouer au prochain tirage.",
    "Les numéros chauds du mois sont 7, 13 et 42.",
    "Cette méthode garantit de gagner au prochain tirage.",
    "Ce portefeuille a une espérance supérieure à celle du précédent.",
    "Jouez ces cinq numéros pour maximiser vos chances.",
    "Une stratégie gagnante consiste à éviter les suites.",
    "Le 13 n'est pas sorti depuis 40 tirages, il devrait revenir.",
    "Cette astuce infaillible augmente vos probabilités.",
]

LEGITIMES = [
    "La probabilité d'au moins un gain est plus élevée avec une couverture de 30 grilles qu'avec 6, "
    "et cette différence est calculée exhaustivement.",
    "Cette classe regroupe 4,4 % des combinaisons possibles.",
    "Ce retard est celui qu'on attend sous hasard pur : le temps d'attente médian est de 21 tirages.",
    "La somme vaut 222, dans une classe de 141 combinaisons sur 2 118 760.",
    "Ces mesures décrivent la forme d'un tirage déjà réalisé ; aucune ne permet de prédire le suivant.",
    "L'espérance de gain d'une mise est négative.",
    "Le nombre de grilles gagnantes attendu sur 30 est de 0,0412 sous la loi exacte.",
    "Aucune de ces mesures ne prédit le prochain tirage.",
    "Quatre numéros se trouvent dans la tranche 41-50, une configuration peu courante.",
]


def self_test():
    echecs = 0
    print("=== phrases qui DOIVENT être refusées ===")
    for phrase in INTERDITES:
        if not lint(phrase):
            print(f"  MANQUÉE : {phrase}")
            echecs += 1
    print(f"  {len(INTERDITES) - echecs}/{len(INTERDITES)} correctement refusées")

    print("\n=== phrases qui DOIVENT passer ===")
    faux_positifs = 0
    for phrase in LEGITIMES:
        infractions = lint(phrase)
        if infractions:
            print(f"  FAUX POSITIF : {phrase}")
            for nom, _, _ in infractions:
                print(f"      règle {nom}")
            faux_positifs += 1
    print(f"  {len(LEGITIMES) - faux_positifs}/{len(LEGITIMES)} correctement acceptées")
    return echecs + faux_positifs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("texte", nargs="?")
    ap.add_argument("--file", type=Path)
    ap.add_argument("--drafts", action="store_true", help="vérifie tous les brouillons du dépôt")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(1 if self_test() else 0)

    if args.drafts:
        code = 0
        n = 0
        for chemin in sorted(ROOT.glob("runs*/*/draft.json")) + sorted(ROOT.glob("runs*/*/article.json")):
            d = json.loads(chemin.read_text(encoding="utf-8"))
            code |= rapport(str(chemin.relative_to(ROOT)), d["draft"]["body"])
            n += 1
        journal = ROOT / "dist" / "articles.json"
        if journal.exists():
            for a in json.loads(journal.read_text(encoding="utf-8"))["articles"]:
                code |= rapport(f"publié : {a['article_id']}", a["draft"]["body"])
                n += 1
        print(f"\n{n} textes vérifiés")
        sys.exit(code)

    texte = args.file.read_text(encoding="utf-8") if args.file else args.texte
    if not texte:
        ap.error("donne un texte, --file, --drafts ou --self-test")
    sys.exit(rapport(args.file.name if args.file else "texte", texte))


if __name__ == "__main__":
    main()
