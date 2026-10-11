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

Version : 0.4 | Date : 2026-10-02 | Auteur : AleaQuant
Historique : 0.4 aligne la production EuroMillions sur le pipeline YAML commun.
TODO : préserver les empreintes des facts liés aux articles approuvés.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from itertools import combinations
from math import comb, prod
from pathlib import Path

from common import (DATA, ENGINE_VERSION, MAIN_CAT, MAIN_FIELDS, PATTERNS, STAR_FIELDS,
                    key, load_patterns, num, sha256_file)
from facts import LABELS, STAR_LABELS, LawIndex, decade_sums_fact, fmt, metric_fact, nb
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
_cache_em_star_index = None


def index_composante(game_id, comp, k, n, rule):
    """Retourne la loi de la composante, y compris le profil historique des étoiles EM."""
    global _cache_em_star_index
    if game_id == "euromillions" and comp == "stars" and rule.jusqua is None:
        if _cache_em_star_index is None:
            laws = json.loads((DATA / "exact_laws.json").read_text(encoding="utf-8"))
            _cache_em_star_index = {
                champ: LawIndex(loi, laws["stars_total"], True)
                for champ, loi in laws["stars"].items()
            }
        return _cache_em_star_index, "", "loi exacte par énumération complète"
    return (*index_regime(k, n),)


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
            corps["total"], corps.get("method", ""))
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
    em_patterns = load_patterns() if game_id == "euromillions" else None

    # historique antérieur, par (composante, k, n) : comparabilité par régime
    vus_valeurs = {}      # (comp, k, n) -> {champ: Counter}
    vus_nombre = Counter()  # (comp, k, n) -> nombre de tirages antérieurs comparables
    vus_signature = {}    # (k, n) -> Counter des signatures de la composante principale
    vus_exact = {}        # (k, n) -> Counter des sélections exactes
    vus_sous = {}         # (k, n) -> Counter des sous-ensembles de taille k-1
    pascal = {t: Counter() for t in (2, 3, 4, 5)}

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
        if game_id == "keno":
            # Au Keno, le joueur choisit une grille de 4 à 10 numéros alors que le
            # tirage contient 16 ou 20 boules. C(n, k) décrit un tirage exact, pas la
            # probabilité de gain d'une grille jouée (qui dépend de sa taille et du rang).
            faits.append({
                "fact_id": "F.draw.probability", "category": "exact_draw",
                "method": "combinatoire exacte",
                "value": {"full_draws": total_grille, "rule_id": regle.id,
                          "draw": {c: {"picks": regle.picks[c], "domain": regle.domains[c]}
                                   for c in grille}},
                "statement": ("Sous la règle en vigueur à la date du tirage — %s —, ce "
                              "tirage exact de %s avait une probabilité de 1 sur %s, "
                              "comme tout autre tirage exact de la même formule. "
                              "Cela ne donne pas la probabilité de gain d’une grille Keno.")
                              % (description, tirees, nb(total_grille)),
            })
        elif game_id == "euromillions":
            main_total = comb(regle.domains["main"], regle.picks["main"])
            stars_total = comb(regle.domains["stars"], regle.picks["stars"])
            faits.append({
                "fact_id": "F.grid.probability", "category": "exact_grid",
                "method": "combinatoire exacte",
                "value": {"full_combinations": total_grille, "rule_id": regle.id,
                          "main_domain": regle.domains["main"],
                          "stars_domain": regle.domains["stars"]},
                "statement": ("Sous la règle en vigueur à la date du tirage — 5 numéros sur %d et "
                              "2 étoiles sur %d —, chaque combinaison complète a la même "
                              "probabilité, 1 sur %s : %s + étoiles %s n’était ni plus ni moins "
                              "probable qu’une autre.") % (
                                  regle.domains["main"], regle.domains["stars"], nb(main_total * stars_total),
                                  "-".join(map(str, valeurs["main"])),
                                  "-".join(map(str, valeurs["stars"]))),
            })
        else:
            faits.append({
                "fact_id": "F.grid.probability", "category": "exact_grid",
                "method": "combinatoire exacte",
                "value": {"full_combinations": total_grille, "rule_id": regle.id,
                          "grid": {c: {"picks": regle.picks[c], "domain": regle.domains[c]}
                                   for c in grille}},
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
            if game_id == "euromillions" and comp == "stars" and regle.jusqua is not None:
                # EuroMillions historique ne publiait pas de lois marginales pour les
                # anciennes règles d'étoiles. Une règle non courante ne les ajoute pas
                # implicitement pendant l'unification.
                continue
            idx, _, method = index_composante(game_id, comp, k, n, regle)
            m = (em_patterns.stars_pattern(nums)
                 if game_id == "euromillions" and comp == "stars"
                 else metriques(nums, n))
            cle_regime = (comp, k, n)
            anterieurs = vus_valeurs.setdefault(cle_regime, {})
            n_prior = vus_nombre[cle_regime]
            champs = ((MAIN_FIELDS + MAIN_CAT) if comp == "main" and game_id == "euromillions"
                      else (STAR_FIELDS if comp == "stars" and game_id == "euromillions"
                            else sorted(idx)))
            for champ in champs:
                if champ not in idx:
                    continue
                index = idx[champ]
                if champ not in m:
                    continue
                v = _valeur(champ, m[champ])
                label = (STAR_LABELS.get(champ, champ) if comp == "stars"
                         else LABELS.get(champ, champ))
                if comp != "main" and not (game_id == "euromillions" and comp == "stars"):
                    label = f"{label} ({_libelle_composante(comp, k)})"
                fact = metric_fact(f"{comp}.{champ}", label, v, index,
                                   anterieurs.get(champ, Counter()), n_prior)
                if method.startswith("récurrences"):
                    fact["method"] = method
                faits.append(fact)
            if comp == "main":
                # Profil descriptif complémentaire ; aucune loi marginale ni rareté
                # n'est attribuée au vecteur des sous-totaux.
                faits.append(decade_sums_fact(nums, n))

        if (game_id == "euromillions" and "stars" in valeurs
                and regle.jusqua is not None):
            faits.append({
                "fact_id": "F.stars.rule", "category": "interpretation", "method": "règlement",
                "statement": "Ce tirage relève d’une ancienne règle des étoiles (%s) : "
                             "ses étoiles ne sont pas comparées à la loi à 12 étoiles." % regle.id,
            })

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
        signature_fact = {
            "fact_id": "F.signature", "category": "historical",
            "method": ("signature patterns.py" if game_id == "euromillions"
                       else "signature de forme"),
            "value": {"signature": sig, "signature_fr": signature_fr, "prior": sig_prior,
                      "draws": n_regime},
            "statement": (("Forme du tirage (%s) déjà observée %d fois sur %d tirages antérieurs."
                           if game_id == "euromillions" else
                           "Forme du tirage (%s) déjà observée %d fois sur %d tirages antérieurs "
                           "de la même formule.") % (signature_fr, sig_prior, n_regime)),
        }
        if game_id != "euromillions":
            faits.append(signature_fact)

        if game_id == "euromillions" and km == 5:
            sub = {}
            for subset_size in (2, 3, 4):
                subsets = list(combinations(principal, subset_size))
                seen = [s for s in subsets if pascal[subset_size].get(s, 0) > 0]
                top = max(subsets, key=lambda s: pascal[subset_size].get(s, 0))
                sub[subset_size] = {
                    "in_draw": len(subsets), "domain": comb(nm, subset_size),
                    "already_seen": len(seen),
                    "most_seen": ["-".join(map(str, top)), pascal[subset_size].get(top, 0)],
                    "expected_seen_per_subset": round(
                        n_regime * comb(nm - subset_size, km - subset_size) / comb(nm, km), 3),
                }
            pascal_fact = {
                "fact_id": "F.pascal.subsets", "category": "exhaustive",
                "method": "combinatoire + historique antérieur", "value": sub,
                "statement": (
                    "Cinq numéros contiennent %d paires et %d triplets : C(5,2) = C(5,3), "
                    "symétrie du triangle de Pascal. Mais le domaine compte %s paires contre "
                    "%s triplets. Avant ce tirage, %d de ses %d paires étaient déjà sorties "
                    "ensemble (la plus fréquente, %s, %d fois), contre %d de ses %d triplets."
                ) % (sub[2]["in_draw"], sub[3]["in_draw"], nb(sub[2]["domain"]),
                     nb(sub[3]["domain"]), sub[2]["already_seen"], sub[2]["in_draw"],
                     sub[2]["most_seen"][0].replace("-", "–"), sub[2]["most_seen"][1],
                     sub[3]["already_seen"], sub[3]["in_draw"]),
            }
            faits.append(pascal_fact)
        repetition = vus_exact.setdefault((km, nm), Counter())[principal]
        sous = vus_sous.setdefault((km, nm), Counter())
        deja = sum(1 for s in combinations(principal, km - 1) if sous[s])
        number_word = "cinq" if game_id == "euromillions" and km == 5 else str(km)
        history_opening = ("Ces %s numéros n’étaient jamais sortis ensemble auparavant" % number_word
                           if repetition == 0 else
                           "Ces %s numéros étaient déjà sortis ensemble %d fois" %
                           (number_word, repetition))
        if game_id == "euromillions" and km == 5:
            history_detail = (". Aucun de ses 5 quadruplets n’avait été tiré." if deja == 0
                              else ". Un de ses 5 quadruplets avait déjà été tiré." if deja == 1
                              else ". %d de ses 5 quadruplets avaient déjà été tirés." % deja)
        else:
            history_detail = ((". Aucun de ses %d sous-ensembles de %d numéros n’avait été tiré."
                               % (km, km - 1)) if deja == 0 else
                              ". %d de ses %d sous-ensembles de %d numéros avaient déjà été tirés."
                              % (deja, km, km - 1))
        history_fact = {
            "fact_id": "F.history.exact_main", "category": "historical",
            "method": ("historique antérieur" if game_id == "euromillions"
                       else "historique antérieur, même formule"),
            "value": ({"count": repetition, "quadruplets_seen": deja}
                      if game_id == "euromillions" and km == 5 else
                      {"count": repetition, "subsets_size": km - 1, "subsets_seen": deja,
                       "subsets_total": km}),
            "statement": history_opening + history_detail,
        }
        faits.append(history_fact)
        if game_id == "euromillions":
            faits.append(signature_fact)

        if seulement is None or t["draw_id"] in seulement:
            if game_id == "euromillions":
                resultats[t["draw_id"]] = {
                    "schema": "aleaquant-draw-facts-v1", "engine": ENGINE_VERSION,
                    "game_id": game_id, "draw_id": t["draw_id"], "date": t["occurred_on"],
                    "rule_id": regle.id, "main": list(principal),
                    "stars": list(valeurs["stars"]),
                    "source": {"publisher": t["source"]["publisher"],
                               "source_id": t["source"]["source_id"],
                               "revision": t["revision"],
                               "revision_sha256": t["sha256"]},
                    "laws_patterns_sha256": sha256_file(PATTERNS),
                    "prior_draws": n_regime, "no_look_ahead": True, "facts": faits,
                }
            else:
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
            m = (em_patterns.stars_pattern(nums)
                 if game_id == "euromillions" and comp == "stars"
                 else metriques(nums, n))
            anterieurs = vus_valeurs.setdefault((comp, k, n), {})
            idx, _, _ = index_composante(game_id, comp, k, n, regle)
            for champ in idx:
                if champ in m:
                    anterieurs.setdefault(champ, Counter())[key(_valeur(champ, m[champ]))] += 1
            vus_nombre[(comp, k, n)] += 1
        vus_signature[(km, nm)][sig] += 1
        vus_exact[(km, nm)][principal] += 1
        for s in combinations(principal, km - 1):
            sous[s] += 1
        if game_id == "euromillions" and km == 5:
            for subset_size in pascal:
                pascal[subset_size].update(combinations(principal, subset_size))

    return resultats


def ecrire(game_id, dossier=ROOT / "dist" / "data" / "facts", *, store=STORE, seulement=None,
           force=False):
    """Écrit des faits reproductibles, éventuellement limités à des draw_id explicites.

    Même en mode sélectif, tout l'historique est parcouru avant chaque tirage retenu.
    Un identifiant inconnu fait échouer le build avant la moindre écriture.
    """
    demandes = set(seulement) if seulement is not None else None
    faits = construire_faits(game_id, store=store, seulement=demandes)
    if demandes is not None:
        absents = demandes - faits.keys()
        if absents:
            raise ValueError("draw_id inconnus pour %s : %s" %
                             (game_id, ", ".join(sorted(absents))))
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    ecrits = 0
    for did, corps in faits.items():
        cible = dossier / f"{did}.json"
        source_sha = corps.get("source", {}).get("revision_sha256")
        if cible.is_file() and not force and source_sha:
            try:
                precedent = json.loads(cible.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                precedent = {}
            if precedent.get("source", {}).get("revision_sha256") == source_sha:
                continue  # préserver les hashes déjà cités par les articles approuvés
        cible.write_text(json.dumps(corps, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
        ecrits += 1
    if game_id == "euromillions":
        latest_id = charger_tirages(game_id, store)[-1]["draw_id"]
        if latest_id in faits:
            (dossier / "latest.json").write_text(
                json.dumps(faits[latest_id], ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8")
    return ecrits


if __name__ == "__main__":
    import argparse
    import time
    parser = argparse.ArgumentParser(description="Faits génériques, par tirage ou par jeu")
    parser.add_argument("games", nargs="+", help="identifiants des jeux")
    parser.add_argument("--draw", action="append", dest="draws", metavar="DRAW_ID",
                        help="tirage à écrire ; répétable, avec un seul jeu")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "data" / "facts",
                        help="dossier de sortie des JSON de faits")
    parser.add_argument("--force", action="store_true",
                        help="réécrit aussi les fiches dont la révision source n'a pas changé")
    args = parser.parse_args()
    if args.draws and len(args.games) != 1:
        parser.error("--draw demande un seul jeu")
    for jeu in args.games:
        t = time.time()
        print(f"{jeu} : {ecrire(jeu, args.output, seulement=args.draws, force=args.force)} "
              f"fichiers de faits en {time.time() - t:.0f}s")
