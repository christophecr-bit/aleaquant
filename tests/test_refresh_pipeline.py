"""AleaQuant · tests du rafraîchissement multi-jeux · v0.7 · 02/10/2026.

Auteur : AleaQuant. Historique : v0.7 vérifie le routage des facts par le builder YAML.
TODO : ajouter l'essai d'intégration sur tranche Keno avec DB de recette.
"""
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import common  # noqa: E402
import rarity_profiles  # noqa: E402

spec = importlib.util.spec_from_file_location("refresh_draws", ROOT / "tools/refresh_draws.py")
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshPipelineTests(unittest.TestCase):
    def test_profil_keno_par_regime_contient_les_deux_formules(self):
        profile = rarity_profiles.build_par_regime("keno", "KE-")
        self.assertIn("main-20-70", profile["regimes"])
        self.assertIn("main-16-56", profile["regimes"])
        self.assertEqual(profile["regimes"]["main-16-56"]["main.sum"]["draws"], 333)
        self.assertEqual(profile["regimes"]["main-20-70"]["main.sum"]["draws"], 19133)

    def test_couverture_keno_exclut_les_faits_absents_ou_a_sha_perime(self):
        with tempfile.TemporaryDirectory() as temp:
            facts_dir = Path(temp)
            current = {
                "KE-ok": {"sha": "sha-ok"},
                "KE-missing": {"sha": "sha-missing"},
                "KE-stale": {"sha": "sha-new"},
            }
            (facts_dir / "KE-ok.json").write_text(json.dumps({
                "draw_id": "KE-ok", "source": {"revision_sha256": "sha-ok"}}))
            (facts_dir / "KE-stale.json").write_text(json.dumps({
                "draw_id": "KE-stale", "source": {"revision_sha256": "sha-old"}}))
            self.assertEqual(refresh.keno_fact_coverage(current, facts_dir), (1, 3))

    def test_verification_keno_exige_page_seulement_pour_regime_actif(self):
        with tempfile.TemporaryDirectory() as temp:
            web = Path(temp) / 'web'
            facts_dir = web / 'dist/data/facts'
            page_dir = web / 'dist/tirages/keno/KE-active'
            facts_dir.mkdir(parents=True)
            page_dir.mkdir(parents=True)
            active = {
                'draw_id': 'KE-active', 'game_id': 'keno', 'date': '2026-10-01',
                'rule_id': 'keno-56-16-v1',
                'source': {'revision_sha256': 'sha-active'},
            }
            legacy = {
                'draw_id': 'KE-legacy', 'game_id': 'keno', 'date': '1993-09-16',
                'rule_id': 'keno-70-20-v1',
                'source': {'revision_sha256': 'sha-legacy'},
            }
            (facts_dir / 'KE-active.json').write_text(json.dumps(active))
            (facts_dir / 'KE-legacy.json').write_text(json.dumps(legacy))
            (page_dir / 'index.html').write_text(
                '<h1>KE-active</h1><svg class="metric-spark"></svg>')
            current = {'KE-active': {'sha': 'sha-active'},
                       'KE-legacy': {'sha': 'sha-legacy'}}

            refresh.verify_facts('keno', ['KE-active', 'KE-legacy'], current,
                                 {'web': web}, pages=True)

    def test_rattrapage_keno_force_tous_les_faits_meme_si_etat_source_a_jour(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = {"web": root / "web", "data": root / "data", "lab": root / "lab",
                 "store": root / "tirages.sqlite3", "state": root / "state.json"}
            snapshots = {game: {f"{prefix}test": {"revision": 1, "sha": game,
                                                "date": "2026-09-29"}}
                         for game, prefix in refresh.PREFIXES.items()}
            p["state"].write_text(json.dumps({
                "schema": refresh.SCHEMA, "computed": snapshots}))
            calls, verified = [], []

            def fake_command(args, *, cwd, env):
                calls.append(args)

            with patch.object(refresh, "ensure_laws"), \
                 patch.object(refresh, "command", side_effect=fake_command), \
                 patch.object(refresh, "revisions", side_effect=lambda _, game: snapshots[game]), \
                 patch.object(refresh, "verify_facts",
                              side_effect=lambda game, ids, *_args, **_kwargs:
                              verified.append((game, ids)) if ids else None):
                self.assertEqual(refresh.run(p, backfill_keno_facts=True), 0)

            keno_builds = [args for args in calls
                           if "engine/facts_generic.py" in args and "keno" in args]
            self.assertEqual(len(keno_builds), 1)
            self.assertNotIn("--draw", keno_builds[0])
            self.assertEqual(verified, [("keno", ["KE-test"])])

    def test_validation_loi_verifie_total_et_masse_de_tous_les_champs(self):
        doc = {"schema": refresh.LAW_SCHEMA, "picks": 2, "domain": 4, "total": 6,
               "fields": ["sum"], "missing_fields": ["span"],
               "laws": {"sum": {"3": 2, "4": 2, "5": 2}}}
        refresh.validate_law_document(doc, 2, 4)
        doc["laws"]["sum"]["3"] = 1
        with self.assertRaisesRegex(ValueError, "masse invalide"):
            refresh.validate_law_document(doc, 2, 4)
        doc["laws"]["sum"]["3"] = True
        with self.assertRaisesRegex(ValueError, "masse invalide"):
            refresh.validate_law_document(doc, 2, 4)

    def test_validation_loi_refuse_un_total_de_regime_errone(self):
        doc = {"schema": refresh.LAW_SCHEMA, "picks": 2, "domain": 4, "total": 5,
               "fields": [], "missing_fields": [], "laws": {}}
        with self.assertRaisesRegex(ValueError, "total invalides"):
            refresh.validate_law_document(doc, 2, 4)

    def test_moteur_euromillions_ignore_les_autres_jeux_du_sqlite(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "tirages.sqlite3"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE revisions(game TEXT, draw_id TEXT, revision INTEGER, "
                        "body TEXT, sha TEXT)")
            em = {"values": [["main", [1, 2, 3, 4, 5]], ["stars", [1, 2]]],
                  "occurred_on": "2026-09-29", "rule_id": "euromillions-50-12-v1",
                  "source": {"source_id": "source", "publisher": "FDJ"}}
            loto = {"values": [["main", [1, 2, 3, 4, 5]], ["chance", [1]]],
                    "occurred_on": "2026-09-28", "rule_id": "loto-49-5-chance-v1",
                    "source": {"source_id": "source", "publisher": "FDJ"}}
            con.executemany("INSERT INTO revisions VALUES(?,?,?,?,?)", [
                ("euromillions", "EM-test", 1, json.dumps(em), "em-sha"),
                ("loto", "LO-test", 1, json.dumps(loto), "lo-sha"),
            ])
            con.commit()
            con.close()
            with patch.object(common, "HISTORY_DB", db):
                draws, _ = common.load_draws()
            self.assertEqual([d["id"] for d in draws], ["EM-test"])

    def test_les_trois_collectes_precedent_leurs_calculs_et_les_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = {"web": root / "web", "data": root / "data", "lab": root / "lab",
                 "store": root / "tirages.sqlite3", "state": root / "state.json"}
            snapshots = {game: {f"{prefix}test": {"revision": 1, "sha": "sha-" + game,
                                                "date": "2026-09-29"}}
                         for game, prefix in refresh.PREFIXES.items()}
            calls = []

            def fake_command(args, *, cwd, env):
                calls.append(" ".join(args[1:]))
                self.assertEqual(env["ALEAQUANT_HISTORY_DB"], str(p["store"]))

            with patch.object(refresh, "ensure_laws"), \
                 patch.object(refresh, "command", side_effect=fake_command), \
                 patch.object(refresh, "revisions", side_effect=lambda _, game: snapshots[game]), \
                 patch.object(refresh, "verify_facts"):
                self.assertEqual(refresh.run(p), 0)
            self.assertEqual(sum("-m aleaquant_data ingest" in c for c in calls), 3)
            self.assertLess(calls.index("-m aleaquant_data ingest keno"),
                            next(i for i, c in enumerate(calls) if "engine/build_data.py" in c))
            build_i = next(i for i, c in enumerate(calls)
                           if "engine/build_data.py --skip-facts" in c)
            em_facts_i = next(i for i, c in enumerate(calls)
                              if "engine/facts_generic.py euromillions" in c)
            self.assertLess(build_i, em_facts_i)
            self.assertLess(em_facts_i, calls.index("engine/build_pages.py"))
            self.assertLess(next(i for i, c in enumerate(calls) if "engine/facts_generic.py loto" in c),
                            calls.index("engine/build_pages.py"))
            self.assertLess(next(i for i, c in enumerate(calls) if "engine/facts_generic.py keno" in c),
                            calls.index("engine/build_pages.py"))
            self.assertTrue(any("build_par_regime; build_par_regime('keno', 'KE-')" in c
                                for c in calls))
            self.assertTrue(any("build_par_regime('euromillions', 'EM-')" in c
                                for c in calls))
            self.assertEqual(set(json.loads(p["state"].read_text())["computed"]),
                             set(refresh.GAMES))

    def test_echec_de_calcul_ne_marque_pas_le_jeu_comme_termine(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = {"web": root / "web", "data": root / "data", "lab": root / "lab",
                 "store": root / "tirages.sqlite3", "state": root / "state.json"}
            snapshots = {game: {f"{prefix}test": {"revision": 1, "sha": game,
                                                "date": "2026-09-29"}}
                         for game, prefix in refresh.PREFIXES.items()}

            def fake_command(args, *, cwd, env):
                if "engine/facts_generic.py" in args and "loto" in args:
                    raise RuntimeError("calcul interrompu")

            with patch.object(refresh, "ensure_laws"), \
                 patch.object(refresh, "command", side_effect=fake_command), \
                 patch.object(refresh, "revisions", side_effect=lambda _, game: snapshots[game]), \
                 patch.object(refresh, "verify_facts"):
                self.assertEqual(refresh.run(p), 1)
            computed = json.loads(p["state"].read_text())["computed"]
            self.assertNotIn("loto", computed)
            self.assertIn("keno", computed)


if __name__ == "__main__":
    unittest.main()
