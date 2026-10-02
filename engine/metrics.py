"""Métriques d'un tirage, génériques : k numéros tirés dans un domaine 1..n.

Version : 0.2 | Date : 2026-10-02 | Auteur : AleaQuant
Historique : 0.2 ajoute les sous-totaux descriptifs par dizaine.
TODO : qualifier une loi exacte marginale par dizaine si un usage de rareté le justifie.

Le laboratoire définit ces métriques pour EuroMillions seul (5 parmi 50, dizaines
1-10…41-50, coupure bas/haut à 25). Ce module les calcule pour n'importe quel couple
(k, n), ce qu'exigent le Loto (6 parmi 49 puis 5 parmi 49) et le Keno (20 parmi 70 puis
16 parmi 56).

Exigence tenue par les tests : pour (5, 50) et (2, 12), ce module renvoie EXACTEMENT ce
que renvoie le laboratoire. Sinon les faits déjà publiés changeraient, et 1 985 pages en
ligne deviendraient fausses sans qu'on l'ait voulu.

Deux conventions, explicites parce qu'elles sont arbitraires :
  - les tranches font dix numéros, la dernière étant tronquée si le domaine ne tombe pas
    juste (1-10 … 41-49 pour le Loto, 51-56 pour le Keno actuel) ;
  - la coupure bas/haut est à ceil(n/2), soit 25 pour 50 — identique à l'existant — et 25
    pour 49, 28 pour 56, 35 pour 70.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from itertools import combinations
from math import comb


def tranches(domain, taille=10):
    """Bornes basses des tranches de `taille` numéros couvrant 1..domain."""
    return tuple(range(1, domain + 1, taille))


def profil_dizaines(numeros, domain, *, taille_tranche=10):
    """Effectif et sous-total des numéros tirés dans chaque tranche de dix.

    Le dernier intervalle est tronqué à `domain` (par exemple 51–56 au Keno 16/56).
    Ces sous-totaux sont descriptifs : cette fonction ne leur attribue ni loi ni rareté.
    """
    valeurs = tuple(sorted(numeros))
    if not valeurs or valeurs[0] < 1 or valeurs[-1] > domain:
        raise ValueError(f"sélection hors du domaine 1-{domain}")
    if len(set(valeurs)) != len(valeurs):
        raise ValueError(f"doublon dans {valeurs}")
    bornes = tranches(domain, taille_tranche)
    effectifs, sous_totaux = [0] * len(bornes), [0] * len(bornes)
    for valeur in valeurs:
        i = (valeur - 1) // taille_tranche
        effectifs[i] += 1
        sous_totaux[i] += valeur
    return tuple({
        "decade": i + 1,
        "start": lo,
        "end": min(lo + taille_tranche - 1, domain),
        "count": effectifs[i],
        "sum": sous_totaux[i],
    } for i, lo in enumerate(bornes))


def coupure_basse(domain):
    """Dernier numéro de la moitié basse : ceil(domain / 2)."""
    return (domain + 1) // 2


def _est_progression_arithmetique(valeurs):
    if len(valeurs) < 3:
        return len(valeurs) >= 2
    pas = valeurs[1] - valeurs[0]
    return all(b - a == pas for a, b in zip(valeurs, valeurs[1:]))


def _plus_longue_progression(valeurs, triples):
    """Longueur de la plus longue progression arithmétique, au moins 2 dès qu'il y a
    deux numéros. Reproduit la logique du laboratoire, y compris son raccourci sur les
    triplets."""
    if len(valeurs) < 2:
        return len(valeurs)
    if _est_progression_arithmetique(valeurs):
        return len(valeurs)
    meilleure = 3 if triples else 2
    ensemble = set(valeurs)
    for a, b in combinations(valeurs, 2):
        pas = b - a
        longueur, suivant = 2, b + pas
        while suivant in ensemble:
            longueur += 1
            suivant += pas
        meilleure = max(meilleure, longueur)
    return meilleure


def metriques(numeros, domain, *, taille_tranche=10):
    """Toutes les métriques d'une sélection, pour un domaine quelconque.

    Une sélection d'un seul numéro (le numéro chance du Loto, par exemple) n'a ni écart
    ni étendue : les champs correspondants sont alors absents, et non mis à zéro — un
    zéro se comparerait à tort à un vrai écart nul.
    """
    valeurs = tuple(sorted(numeros))
    k = len(valeurs)
    if k == 0:
        raise ValueError("sélection vide")
    if valeurs[0] < 1 or valeurs[-1] > domain:
        raise ValueError(f"{valeurs} hors du domaine 1-{domain}")
    if len(set(valeurs)) != k:
        raise ValueError(f"doublon dans {valeurs}")

    resultat = {
        "numbers": valeurs,
        "sum": sum(valeurs),
        "odd_count": sum(v % 2 for v in valeurs),
        "low_count": sum(v <= coupure_basse(domain) for v in valeurs),
    }
    resultat["even_count"] = k - resultat["odd_count"]
    resultat["high_count"] = k - resultat["low_count"]

    terminaux = Counter(v % 10 for v in valeurs)
    resultat["repeated_terminal_digits"] = sum(c - 1 for c in terminaux.values())
    resultat["terminal_pair_collisions"] = sum(comb(c, 2) for c in terminaux.values())

    profil = profil_dizaines(valeurs, domain, taille_tranche=taille_tranche)
    decades = tuple(b["count"] for b in profil)
    resultat["decade_counts"] = decades
    resultat["decade_sums"] = tuple(b["sum"] for b in profil)
    resultat["max_same_decade"] = max(decades)
    resultat["occupied_decades"] = sum(c > 0 for c in decades)

    if k == 1:
        return resultat

    ecarts = tuple(b - a for a, b in zip(valeurs, valeurs[1:]))
    suites, courante = [], 1
    for ecart in ecarts:
        if ecart == 1:
            courante += 1
        else:
            suites.append(courante)
            courante = 1
    suites.append(courante)
    triples = sum(a + c == 2 * b for a, b, c in combinations(valeurs, 3)) if k >= 3 else 0

    resultat.update({
        "gaps": ecarts,
        "sorted_gaps": tuple(sorted(ecarts)),
        "min_gap": min(ecarts),
        "max_gap": max(ecarts),
        "mean_gap": str(Fraction(sum(ecarts), len(ecarts))),
        "span": valeurs[-1] - valeurs[0],
        "longest_consecutive_run": max(suites),
        "consecutive_pairs": sum(e == 1 for e in ecarts),
        "runs_ge2": sum(longueur >= 2 for longueur in suites),
        "is_arithmetic_progression": _est_progression_arithmetique(valeurs),
        "longest_arithmetic_progression": _plus_longue_progression(valeurs, triples),
        "arithmetic_triples": triples,
        "clusteredness_close_pairs_5": sum(b - a <= 5 for a, b in combinations(valeurs, 2)),
    })
    return resultat


def signature(m):
    """Signature de forme, lisible, indépendante du jeu."""
    return "run={};decade_max={};decades={}".format(
        m.get("longest_consecutive_run", 1), m["max_same_decade"], m["occupied_decades"])
