"""Contrôles de la relecture de fluidité, sans modèle ni réseau.

Nom : tests/test_editorial_polish.py · Version : 0.1 · Date : 2026-09-30
Auteur : AleaQuant · Historique : nombre, rareté et SHA du brouillon révisé.
TODO : élargir l'évaluation de qualité sur des articles réels.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
from editorial_polish import polish, validate_polish  # noqa: E402
from guards import build_compose_article, run_all_guards  # noqa: E402
from draw_report import digest  # noqa: E402


class EditorialPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts_path = ROOT / "dist" / "data" / "facts" / "EM-26078.json"
        cls.facts = json.loads(cls.facts_path.read_text(encoding="utf-8"))

    def article(self):
        text = "La somme des cinq numéros vaut 98.\n\nLes cinq numéros occupent 4 dizaines."
        article = build_compose_article(self.facts_path, self.facts, text,
                                        run_all_guards(text, self.facts))
        article["provenance"]["facts_path"] = str(self.facts_path)
        return article

    def test_relecture_fidele_et_nouveau_sha(self):
        article = self.article()
        revised = "La somme atteint 98 pour ces cinq numéros.\n\nAu total, 4 dizaines sont occupées par les cinq numéros."
        validate_polish(article, revised, self.facts)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "draft.json"
            path.write_text(json.dumps(article, ensure_ascii=False))
            out = polish(path, revised)
            new = json.loads(out.read_text())
            self.assertEqual(new["draft"]["title"], article["draft"]["title"])
            self.assertEqual(new["draft_sha256"], digest(new["draft"]))
            self.assertNotEqual(new["draft_sha256"], article["draft_sha256"])
            self.assertEqual(new["status"], "PENDING_HUMAN")

    def test_nombre_change_bloque(self):
        with self.assertRaisesRegex(ValueError, "nombres modifiés"):
            validate_polish(self.article(),
                            "La somme vaut 99.\n\nLes cinq numéros occupent 4 dizaines.",
                            self.facts)

    def test_promesse_predictive_bloquee(self):
        with self.assertRaisesRegex(ValueError, "contrôle scientifique"):
            validate_polish(self.article(),
                            "La somme des cinq numéros vaut 98.\n\n"
                            "Les cinq numéros occupent 4 dizaines et prédisent le prochain tirage.",
                            self.facts)


if __name__ == "__main__":
    unittest.main()
