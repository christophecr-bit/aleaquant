"""Provenance du modèle batch — AleaQuant, 2026-09-30, version 0.1.

Historique : les options du workflow agentique ne doivent pas attribuer un
autre modèle au brouillon. TODO : relever les prix par modèle depuis un barème.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

from agent.compose_batch_collect import traiter
from agent import compose_batch_submit
from agent.draw_report import digest

ROOT = Path(__file__).resolve().parents[1]


class BatchConfigurationTests(unittest.TestCase):
    def test_soumission_mockee_transporte_le_profil_dans_le_manifeste(self):
        class FakeFiles:
            def create(self, **kwargs):
                return type("Uploaded", (), {"id": "file-test"})()

        class FakeBatches:
            def __init__(self):
                self.options = None

            def create(self, **kwargs):
                self.options = kwargs
                return type("Batch", (), {"id": "batch_test", "status": "validating"})()

        class FakeClient:
            def __init__(self, **kwargs):
                self.files = FakeFiles()
                self.batches = batches

        batches = FakeBatches()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = ["compose_batch_submit.py", "--n", "1", "--out", str(root / "drafts"),
                    "--model", "modele-essai", "--reasoning-effort", "medium",
                    "--workflow-config-sha", "a" * 64]
            with patch.object(compose_batch_submit, "MANIFEST_DIR", root / "manifests"), \
                 patch.object(compose_batch_submit, "load_key", return_value="fake"), \
                 patch("openai.OpenAI", FakeClient), patch.object(sys, "argv", args):
                compose_batch_submit.main()
            manifest = json.loads((root / "manifests/batch_test.manifest.json").read_text())
            self.assertEqual(manifest["model"], "modele-essai")
            self.assertEqual(manifest["reasoning_effort"], "medium")
            self.assertEqual(manifest["workflow_config_sha256"], "a" * 64)
            self.assertEqual(len(manifest["draws"][next(iter(manifest["draws"]))]["facts_sha256"]), 64)
            self.assertEqual(len(manifest["draws"][next(iter(manifest["draws"]))]["prompt_sha256"]), 64)
            self.assertEqual(batches.options["completion_window"], "24h")
            line = json.loads(next((root / "manifests").glob("compose_input_*.jsonl")).read_text())
            self.assertEqual(line["body"]["model"], "modele-essai")
            self.assertEqual(line["body"]["reasoning"]["effort"], "medium")

    def test_modele_change_provenance_et_sha_sans_estimation_fausse(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            manifest = {"EM-26078": {
                "facts_path": str(ROOT / "dist/data/facts/EM-26078.json"),
                "date": "2026-09-29",
            }}
            response = {"custom_id": "EM-26078", "response": {"body": {
                "output_text": "Les cinq numéros occupent 4 dizaines.",
                "model": "modele-essai",
                "usage": {"input_tokens": 100, "output_tokens": 20},
            }}}
            ok, blocked, failed, cost, _ = traiter(
                json.dumps(response), manifest, out, batch_model="modele-essai")
            self.assertEqual((ok, blocked, failed), (1, 0, 0))
            self.assertIsNone(cost)
            article = json.loads((out / "EM-26078/draft.json").read_text())
            self.assertEqual(article["provenance"]["model"], "modele-essai")
            self.assertIn("modele-essai", article["draft"]["writer"])
            self.assertEqual(article["draft_sha256"], digest(article["draft"]))

    def test_faits_modifies_depuis_soumission_bloquent_la_collecte(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            facts = root / "facts.json"
            facts.write_text(json.dumps({"draw_id": "EM-test", "facts": []}))
            manifest = {"EM-test": {"facts_path": str(facts), "facts_sha256": "0" * 64}}
            response = {"custom_id": "EM-test", "response": {"body": {
                "output_text": "Texte reçu", "usage": {}}}}
            result = traiter(json.dumps(response), manifest, root / "drafts")
            self.assertEqual(result[:3], (0, 0, 1))
            self.assertFalse((root / "drafts/EM-test/draft.json").exists())


if __name__ == "__main__":
    unittest.main()
