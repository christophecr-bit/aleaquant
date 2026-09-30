"""Régressions du chaînage collecte → faits → pages, sans réseau ni FDJ."""
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

spec = importlib.util.spec_from_file_location("refresh_draws", ROOT / "tools/refresh_draws.py")
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshPipelineTests(unittest.TestCase):
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

            with patch.object(refresh, "command", side_effect=fake_command), \
                 patch.object(refresh, "revisions", side_effect=lambda _, game: snapshots[game]), \
                 patch.object(refresh, "verify_facts"):
                self.assertEqual(refresh.run(p), 0)
            self.assertEqual(sum("-m aleaquant_data ingest" in c for c in calls), 3)
            self.assertLess(calls.index("-m aleaquant_data ingest keno"),
                            next(i for i, c in enumerate(calls) if "engine/build_data.py" in c))
            self.assertLess(next(i for i, c in enumerate(calls) if "engine/facts_generic.py loto" in c),
                            calls.index("engine/build_pages.py"))
            self.assertLess(next(i for i, c in enumerate(calls) if "engine/facts_generic.py keno" in c),
                            calls.index("engine/build_pages.py"))
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

            with patch.object(refresh, "command", side_effect=fake_command), \
                 patch.object(refresh, "revisions", side_effect=lambda _, game: snapshots[game]), \
                 patch.object(refresh, "verify_facts"):
                self.assertEqual(refresh.run(p), 1)
            computed = json.loads(p["state"].read_text())["computed"]
            self.assertNotIn("loto", computed)
            self.assertIn("keno", computed)


if __name__ == "__main__":
    unittest.main()
