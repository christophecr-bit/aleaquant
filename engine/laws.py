"""Lois exactes par régime, sans échantillonnage.

Un régime est un couple (nombre tiré, domaine) : EuroMillions 5 parmi 50, Loto 6 puis 5
parmi 49, Keno 20 parmi 70 puis 16 parmi 56. Les lois ne sont PAS une propriété du jeu :
elles appartiennent au régime, et mélanger deux régimes produit des raretés inventées.

Deux méthodes, toutes deux exactes :
  - **énumération** quand l'espace est parcourable (jusqu'à ~20 millions) ;
  - **récurrence** au-delà, où l'énumération est hors de portée : C(56,16) vaut 4,2×10¹³
    et C(70,20) 1,6×10¹⁷. Les lois marginales restent calculables exactement par
    programmation dynamique — voir laws_recurrence.py.

Aucun Monte-Carlo ici. Le total de chaque loi doit valoir C(n,k) exactement : c'est une
preuve arithmétique, vérifiée à chaque construction.
"""
from __future__ import annotations

import json
from collections import Counter
from itertools import combinations
from math import comb
from pathlib import Path

from metrics import metriques

# au-delà, l'énumération n'est plus raisonnable dans ce moteur (le HPC local, lui, tient
# C(56,16) en ~1 h 45 ; ce n'est pas le rôle d'une séance de build)
PLAFOND_ENUMERATION = 20_000_000

# champs dont on construit la loi ; les autres sont des vues (numbers, gaps...)
CHAMPS_SCALAIRES = (
    "sum", "span", "min_gap", "max_gap", "mean_gap", "longest_consecutive_run",
    "consecutive_pairs", "runs_ge2", "max_same_decade", "occupied_decades",
    "odd_count", "low_count", "repeated_terminal_digits", "terminal_pair_collisions",
    "is_arithmetic_progression", "longest_arithmetic_progression", "arithmetic_triples",
    "clusteredness_close_pairs_5",
)
CHAMPS_CATEGORIELS = ("sorted_gaps", "decade_counts")


def cle(valeur):
    """Clé texte stable d'une valeur de métrique, identique à engine/common.key()."""
    from common import key
    return key(valeur)


def enumerable(k, domain):
    return comb(domain, k) <= PLAFOND_ENUMERATION


def lois_par_enumeration(k, domain, *, progression=None):
    """Loi exacte de chaque métrique, par parcours complet de C(domain, k)."""
    total = comb(domain, k)
    if total > PLAFOND_ENUMERATION:
        raise ValueError(
            f"{k} parmi {domain} : {total:,} combinaisons, au-delà du plafond "
            f"d'énumération ({PLAFOND_ENUMERATION:,}). Utiliser les récurrences."
            .replace(",", " "))
    champs = [c for c in CHAMPS_SCALAIRES + CHAMPS_CATEGORIELS]
    lois = {c: Counter() for c in champs}
    fait = 0
    for selection in combinations(range(1, domain + 1), k):
        m = metriques(selection, domain)
        for c in champs:
            if c in m:
                lois[c][cle(m[c])] += 1
        fait += 1
        if progression and fait % progression == 0:
            print(f"    {fait:>12,} / {total:,}".replace(",", " "), flush=True)
    # preuve arithmétique : chaque loi doit totaliser exactement C(domain, k)
    for c, loi in lois.items():
        somme = sum(loi.values())
        if loi and somme != total:
            raise AssertionError(f"loi {c} de {k}/{domain} : {somme} != {total}")
    return {c: dict(loi) for c, loi in lois.items() if loi}, total


def chemin_loi(k, domain, dossier):
    return Path(dossier) / f"regime-{k}-{domain}.json"


def construire(k, domain, dossier, *, force=False, progression=None):
    """Construit et enregistre la loi d'un régime. Idempotent."""
    chemin = chemin_loi(k, domain, dossier)
    if chemin.exists() and not force:
        return json.loads(chemin.read_text(encoding="utf-8")), False
    lois, total = lois_par_enumeration(k, domain, progression=progression)
    corps = {
        "schema": "aleaquant-regime-laws-v1",
        "picks": k, "domain": domain, "total": total,
        "method": "énumération exhaustive, aucun échantillonnage",
        "fields": sorted(lois),
        "laws": lois,
    }
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(corps, ensure_ascii=False, sort_keys=True) + "\n",
                      encoding="utf-8")
    return corps, True


# --- construction reprenable, pour les régimes longs --------------------------------
#
# Une séance de build ne peut pas tenir un calcul de dix minutes d'un seul tenant. On
# découpe donc l'énumération selon le plus petit numéro de la sélection : la tranche
# « premier = i » parcourt C(domain - i, k - 1) combinaisons. Chaque tranche est écrite
# sur disque dès qu'elle est finie ; une reprise saute les tranches déjà faites. La
# fusion finale revérifie que chaque loi totalise exactement C(domain, k).


def _tranche(k, domain, premier):
    champs = CHAMPS_SCALAIRES + CHAMPS_CATEGORIELS
    lois = {c: Counter() for c in champs}
    n = 0
    for reste in combinations(range(premier + 1, domain + 1), k - 1):
        m = metriques((premier,) + reste, domain)
        for c in champs:
            if c in m:
                lois[c][cle(m[c])] += 1
        n += 1
    return {c: dict(v) for c, v in lois.items() if v}, n


def construire_reprenable(k, domain, dossier, *, budget_s=150):
    """Avance la construction d'un régime pendant au plus `budget_s` secondes.

    Retourne (terminé, message). À rappeler jusqu'à terminé=True.
    """
    import time
    final = chemin_loi(k, domain, dossier)
    if final.exists():
        return True, "déjà construit"
    partiel = Path(dossier) / f".partiel-{k}-{domain}"
    partiel.mkdir(parents=True, exist_ok=True)
    premiers = range(1, domain - k + 2)
    debut = time.time()
    traitees = 0
    for p in premiers:
        f = partiel / f"premier-{p:03d}.json"
        if f.exists():
            continue
        # Au moins UNE tranche par appel, quel que soit le budget. Sinon un budget trop
        # court renverrait « reprendre » indéfiniment sans jamais avancer — un livelock
        # que le test des tranches a révélé.
        if traitees and time.time() - debut > budget_s:
            faites = len(list(partiel.glob("premier-*.json")))
            return False, f"{faites}/{len(premiers)} tranches faites, reprendre"
        lois, n = _tranche(k, domain, p)
        attendu = comb(domain - p, k - 1)
        if n != attendu:
            raise AssertionError(f"tranche {p} : {n} combinaisons au lieu de {attendu}")
        f.write_text(json.dumps({"premier": p, "n": n, "laws": lois}), encoding="utf-8")
        traitees += 1

    # fusion
    total = comb(domain, k)
    fusion = {}
    vus = 0
    for f in sorted(partiel.glob("premier-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        vus += d["n"]
        for champ, loi in d["laws"].items():
            cible = fusion.setdefault(champ, Counter())
            for cle_, n in loi.items():
                cible[cle_] += n
    if vus != total:
        raise AssertionError(f"{vus} combinaisons parcourues au lieu de {total}")
    for champ, loi in fusion.items():
        if sum(loi.values()) != total:
            raise AssertionError(f"loi {champ} : {sum(loi.values())} != {total}")
    corps = {
        "schema": "aleaquant-regime-laws-v1", "picks": k, "domain": domain, "total": total,
        "method": "énumération exhaustive par tranches reprenables, aucun échantillonnage",
        "fields": sorted(fusion), "laws": {c: dict(v) for c, v in fusion.items()},
    }
    final.write_text(json.dumps(corps, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    for f in partiel.glob("premier-*.json"):
        f.unlink()
    partiel.rmdir()
    return True, f"terminé : {total} combinaisons, {len(fusion)} lois"
