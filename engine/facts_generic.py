"""Faits d'un tirage, pour n'importe quel jeu décrit dans aleaquant-data/games/*.yaml.

Réutilise tels quels metric_fact(), LawIndex et les formateurs de facts.py : les faits
produits ont EXACTEMENT le format de ceux d'EuroMillions, donc les gardes, les puces de
rareté et les pages les consomment sans modification.

Trois règles qui n'existaient pas dans le pilote EuroMillions, parce qu'EuroMillions ne
les mettait jamais à l'épreuve :

1. **Comparabilité par régime.** Un tirage n'est comparé qu'aux tirages antérieurs dont
   la composante a le même couple (nombre tiré, domaine). Une somme de six numéros ne se
   compare pas à une somme de cinq ; un tirage Keno de 16 boules pas à un de 20.
2. **Probabilité de la grille, pas du tirage.** Seules les composantes que le joueur coche
   entrent dans la probabilité du gros lot (in_grid dans la configuration). La
   complémentaire du Loto d'avant 2008 était tirée mais jamais cochée.
3. **Pas de faits de forme sur un numéro seul.** Le numéro chance est uniformément
   réparti : sa « rareté » ne porte aucune information. Il compte dans la probabilité de
   la grille, pas dans les métriques.

Anti look-ahead : chaque tirage n'est comparé qu'aux tirages strictement antérieurs, dans
l'ordre (date, session) — le premier tirage d'une journée avant le second.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from itertools import combinations
from math import comb, prod
from pathlib import Path

from common import ENGINE_VERSION, key, num
from facts import LABELS, LawIndex, fmt, metric_fact, nb
from metrics import metriques, signature

ROOT = Path(__file__).resolve().parents[1]
DATA_REPO = ROOT.parent / "aleaquant-data"
STORE = DATA_REPO / "data" / "aleaquant.sqlite3"
LOIS = ROOT / "dist" / "data" / "laws"

sys.path.insert(0, str(DATA_REPO))
from aleaquant_data import charger  # noqa: E402

COMPOSANTES_FR = {
    "main": ("numéro", "numéros"),
    "stars": ("étoile", "étoiles"),
    "chance": ("numéro chance", "numéros chance"),
    "complementaire": ("numéro complémentaire", "numéros complémentaires"),
}
CATEGORIELS = {"sorted_gaps", "decade_counts"}


def _libelle_composante(nom, k):
    singulier, pluriel = COMPOSANTES_FR.get(nom, (nom, nom))
    return singulier if k == 1 else pluriel


def charger_config(game_id):
    return charger(DATA_REPO / "games" / f"{game_id}.yaml")


def charger_tirages(game_id, store=STORE):
    """Dernière révision de chaque tirage, dans l'ordre (date, session)."""
    conn = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    lignes = conn.execute(
        "SELECT body, sha FROM revisions r WHERE game=? AND revision=("
        " SELECT MAX(revision) FROM revisions r2 WHERE r2.game=r.game AND r2.draw_id=r.draw_id)",
        (game_id,))
    tirages = []
    for corps, sha in lignes:
        t = json.loads(corps)
        # l'empreinte de référence est la colonne de la table : les révisions reprises du
        # laboratoire ne la portent pas dans leur corps JSON
        t["sha256"] = sha
        tirages.append(t)
    tirages.sort(key=lambda t: (t["occurred_on"], str(t.get("session") or "")))
    return tirages


_cache_index = {}


def index_regime(k, n):
    """LawIndex de chaque champ, pour le régime (k, n). Lève si la loi n'est pas construite."""
    if (k, n) not in _cache_index:
        chemin = LOIS / f"regime-{k}-{n}.json"
        if not chemin.exists():
            raise FileNotFoundError(
                f"loi du régime {k}/{n} absente ({chemin.name}) : la construire avec "
                f"engine/laws.py, ou par récurrence si l'énumération est hors de portée")
        corps = json.loads(chemin.read_text(encoding="utf-8"))
        _cache_index[(k, n)] = (
            {champ: LawIndex(loi, corps["total"], champ not in CATEGORIELS)
             for champ, loi in corps["laws"].items()},
            corps["total"])
    return _cache_index[(k, n)]


def _valeur(champ, v):
    return tuple(v) if champ in CATEGORIELS else num(v)


def construire_faits(game_id, store=STORE, *, seulement=None):
    """Faits de tous les tirages d'un jeu. `seulement` restreint les tirages écrits,
    mais l'historique antérieur reste parcouru en entier (sinon les comparaisons
    seraient fausses)."""
    config = charger_config(game_id)
    regles = {r.id: r for r in config.rules}
    tirages = charger_tirages(game_id, store)

    # historique antérieur, par (composante, k, n) : comparabilité par régime
    vus_valeurs = {}      # (comp, k, n) -> {champ: Counter}
    vus_nombre = Counter()  # (comp, k, n) -> nombre de tirages antérieurs comparables
    vus_signature = {}    # (k, n) -> Counter des signatures de la composante principale
    vus_exact = {}        # (k, n) -> Counter des sélections exactes
    vus_sous = {}         # (k, n) -> Counter des sous-ensembles de taille k-1

    resultats = {}
    for t in tirages:
        regle = regles[t["rule_id"]]
        valeurs = {nom: tuple(v) for nom, v in t["values"]}
        faits = []

        # 1. probabilité de la grille : composantes cochées par le joueur seulement
        grille = config.composantes_grille(regle)
        total_grille = prod(comb(regle.domains[c], regle.picks[c]) for c in grille)
        description = " et ".join(
            f"{regle.picks[c]} {_libelle_composante(c, regle.picks[c])} sur {regle.domains[c]}"
            for c in grille)
        tirees = " + ".join("-".join(map(str, valeurs[c])) for c in grille)
        faits.append({
            "fact_id": "F.grid.probability", "category": "exact_grid",
            "method": "combinatoire exacte",
            "value": {"full_combinations": total_grille, "rule_id": regle.id,
                      "grid": {c: {"picks": regle.picks[c], "domain": regle.domains[c]} for c in grille}},
            "statement": ("Sous la règle en vigueur à la date du tirage — %s —, chaque "
                          "combinaison gagnante a la même probabilité, 1 sur %s : %s n’était ni "
                          "plus ni moins probable qu’une autre.") % (description, nb(total_grille), tirees),
        })
        faits.append({
            "fact_id": "F.editorial.expectation", "category": "interpretation",
            "method": "principe éditorial AleaQuant",
            "statement": ("L’espérance de gain d’une mise est négative. Ces mesures décrivent "
                          "la forme du tirage ; elles ne permettent pas de prédire le suivant."),
        })

        # 2. faits de forme, composante par composante, comparés au seul régime identique
        for comp, nums in valeurs.items():
            k, n = regle.picks[comp], regle.domains[comp]
            if k == 1:
                continue   # un numéro seul est uniforme : aucune information de forme
            idx, _ = index_regime(k, n)
            m = metriques(nums, n)
            cle_regime = (comp, k, n)
            anterieurs = vus_valeurs.setdefault(cle_regime, {})
            n_prior = vus_nombre[cle_regime]
            for champ, index in sorted(idx.items()):
                if champ not in m:
                    continue
                v = _valeur(champ, m[champ])
                label = LABELS.get(champ, champ)
                if comp != "main":
                    label = f"{label} ({_libelle_composante(comp, k)})"
                faits.append(metric_fact(f"{comp}.{champ}", label, v, index,
                                         anterieurs.get(champ, Counter()), n_prior))

        # 3. historique de la composante principale, au sein du régime
        principal = valeurs["main"]
        km, nm = regle.picks["main"], regle.domains["main"]
        mm = metriques(principal, nm)
        sig = signature(mm)
        sig_prior = vus_signature.setdefault((km, nm), Counter())[sig]
        n_regime = vus_nombre[("main", km, nm)]
        signature_fr = ("suite consécutive maximale de %s, maximum de %s numéros dans une même "
                        "dizaine, %s dizaines occupées") % (
            mm.get("longest_consecutive_run", 1), mm["max_same_decade"], mm["occupied_decades"])
        faits.append({
            "fact_id": "F.signature", "category": "historical", "method": "signature de forme",
            "value": {"signature": sig, "signature_fr": signature_fr, "prior": sig_prior,
                      "draws": n_regime},
            "statement": ("Forme du tirage (%s) déjà observée %d fois sur %d tirages antérieurs "
                          "de la même formule.") % (signature_fr, sig_prior, n_regime),
        })
        repetition = vus_exact.setdefault((km, nm), Counter())[principal]
        sous = vus_sous.setdefault((km, nm), Counter())
        deja = sum(1 for s in combinations(principal, km - 1) if sous[s])
        faits.append({
            "fact_id": "F.history.exact_main", "category": "historical",
            "method": "historique antérieur, même formule",
            "value": {"count": repetition, "subsets_size": km - 1, "subsets_seen": deja,
                      "subsets_total": km},
            "statement": (("Ces %d numéros n’étaient jamais sortis ensemble auparavant" % km
                           if repetition == 0 else
                           "Ces %d numéros étaient déjà sortis ensemble %d fois" % (km, repetition))
                          + (". Aucun de ses %d sous-ensembles de %d numéros n’avait été tiré."
                             % (km, km - 1) if deja == 0 else
                             ". %d de ses %d sous-ensembles de %d numéros avaient déjà été tirés."
                             % (deja, km, km - 1))),
        })

        if seulement is None or t["draw_id"] in seulement:
            resultats[t["draw_id"]] = {
                "schema": "aleaquant-draw-facts-v1", "engine": ENGINE_VERSION + "-generic",
                "game_id": game_id, "draw_id": t["draw_id"], "date": t["occurred_on"],
                "session": t.get("session"), "rule_id": regle.id,
                "components": {c: list(v) for c, v in valeurs.items()},
                "main": list(principal),
                "source": {"publisher": t["source"]["publisher"],
                           "source_id": t["source"]["source_id"],
                           "revision": t["revision"], "revision_sha256": t["sha256"]},
                "prior_draws": n_regime, "prior_scope": "même formule",
                "no_look_ahead": True, "facts": faits,
            }

        # mise à jour de l'historique APRÈS le calcul : pas de look-ahead
        for comp, nums in valeurs.items():
            k, n = regle.picks[comp], regle.domains[comp]
            if k == 1:
                continue
            m = metriques(nums, n)
            anterieurs = vus_valeurs.setdefault((comp, k, n), {})
            idx, _ = index_regime(k, n)
            for champ in idx:
                if champ in m:
                    anterieurs.setdefault(champ, Counter())[key(_valeur(champ, m[champ]))] += 1
            vus_nombre[(comp, k, n)] += 1
        vus_signature[(km, nm)][sig] += 1
        vus_exact[(km, nm)][principal] += 1
        for s in combinations(principal, km - 1):
            sous[s] += 1

    return resultats


def ecrire(game_id, dossier=ROOT / "dist" / "data" / "facts"):
    """Écrit les faits d'un jeu. Refuse EuroMillions : ses faits publiés passent encore
    par facts.py, et ce pilote n'a été validé contre eux que pour la composante
    principale (39 700 faits identiques), pas pour les étoiles."""
    if game_id == "euromillions":
        raise SystemExit("EuroMillions reste sur engine/facts.py : bascule non décidée")
    faits = construire_faits(game_id)
    dossier.mkdir(parents=True, exist_ok=True)
    for did, corps in faits.items():
        (dossier / f"{did}.json").write_text(
            json.dumps(corps, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(faits)


if __name__ == "__main__":
    import time
    for jeu in sys.argv[1:]:
        t = time.time()
        print(f"{jeu} : {ecrire(jeu)} fichiers de faits en {time.time() - t:.0f}s")
