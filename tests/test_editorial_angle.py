"""Contrats du choix d'angle A/B/C, sans appel API.

Nom : tests/test_editorial_angle.py · Version : 0.2 · Date : 2026-10-02
Auteur : AleaQuant · Historique : titres finaux nomment jeu et date ; preuves et sélection.
TODO : comparer qualitativement les titres sur un lot réel avant déploiement.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
from editorial_angle import (choose, facts_for, load_selected, propose, revise,
                             validate_option, validate_options)  # noqa: E402
from guards import build_compose_article, guard_decade_ranges, run_all_guards  # noqa: E402
from draw_report import digest  # noqa: E402
from compose_batch_submit import build_jsonl  # noqa: E402
from compose_batch_collect import traiter  # noqa: E402


def options():
    return {"options": [
        {"id": "A", "title": "Une grille qui traverse quatre dizaines",
         "angle": "Les quatre décades occupées donnent une lecture de la géométrie.",
         "evidence_ids": ["F.main.occupied_decades"]},
        {"id": "B", "title": "Ces cinq numéros, jamais ensemble",
         "angle": "L'historique n'avait jamais réuni ces cinq numéros principaux.",
         "evidence_ids": ["F.history.exact_main"]},
        {"id": "C", "title": "La somme s'arrête à 98",
         "angle": "La somme de 98 propose une autre porte d'entrée dans le tirage.",
         "evidence_ids": ["F.main.sum"]},
    ]}


class EditorialAngleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts, _ = facts_for("EM-26078")

    def test_trois_angles_avec_preuves(self):
        self.assertEqual(len(validate_options(options(), self.facts)), 3)

    def test_quantite_absente_du_fait_refusee(self):
        option = options()["options"][0]
        option["title"] = "Une grille qui traverse six dizaines"
        with self.assertRaisesRegex(ValueError, "quantités absentes"):
            validate_option(option, self.facts)

    def test_fait_absent_refuse(self):
        option = options()["options"][0]
        option["evidence_ids"] = ["F.invented"]
        with self.assertRaisesRegex(ValueError, "absent"):
            validate_option(option, self.facts)

    def test_promesse_et_plage_de_decade_refusees(self):
        option = options()["options"][0]
        option["title"] = "Une grille qui prédit le prochain tirage"
        with self.assertRaisesRegex(ValueError, "interdite"):
            validate_option(option, self.facts)
        option["title"] = "Une grille entre 21–30 et 31–40"
        with self.assertRaisesRegex(ValueError, "décades"):
            validate_option(option, self.facts)
        self.assertEqual(guard_decade_ranges("Les numéros en 21–30 et 31-40."),
                         ["21–30", "31-40"])

    def test_selection_liee_aux_faits_et_propositions(self):
        with tempfile.TemporaryDirectory() as folder:
            proposal = propose("EM-26078", json.dumps(options(), ensure_ascii=False),
                               out_dir=Path(folder))
            selected = choose(proposal, "A")
            self.assertEqual(load_selected(selected, self.facts)["title"],
                             "Une grille qui traverse quatre dizaines")
            data = json.loads(proposal.read_text())
            data["options"][0]["title"] = "Titre modifié après choix"
            proposal.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "propositions ont changé"):
                load_selected(selected, self.facts)

    def test_relecture_humaine_du_titre_avant_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            proposal = propose("EM-26078", json.dumps(options(), ensure_ascii=False),
                               out_dir=Path(folder))
            revise(proposal, "A", "Une grille qui parcourt quatre dizaines")
            selected = choose(proposal, "A")
            self.assertEqual(load_selected(selected, self.facts)["title"],
                             "Une grille qui parcourt quatre dizaines")
            with self.assertRaisesRegex(ValueError, "sélection existe déjà"):
                revise(proposal, "A", "Une grille qui traverse quatre dizaines")

    def test_titre_choisi_dans_brouillon_sous_sha(self):
        path = ROOT / "dist" / "data" / "facts" / "EM-26078.json"
        angle = options()["options"][0]
        text = "Les cinq numéros occupent quatre décades."
        guards = run_all_guards(text, self.facts)
        article = build_compose_article(path, self.facts, text, guards, angle=angle)
        self.assertEqual(article["draft"]["title"],
                         "EuroMillions — tirage du 29 septembre 2026 : " + angle["title"])
        self.assertEqual(article["draft"]["editorial_angle"], angle)
        self.assertEqual(article["draft_sha256"], digest(article["draft"]))

    def test_batch_reste_independant_des_angles_experimentaux(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            proposal = propose("EM-26078", json.dumps(options(), ensure_ascii=False),
                               out_dir=root / "angles")
            choose(proposal, "A")
            lines, manifest, ignored = build_jsonl([["EM-26078"]], root / "drafts")
            self.assertEqual(ignored, 0)
            self.assertNotIn("Une grille qui traverse quatre dizaines", lines[0]["body"]["input"])
            self.assertNotIn("Nomme les décades par leur rang", lines[0]["body"]["input"])
            self.assertNotIn("r. Écris des paragraphes reliés", lines[0]["body"]["input"])
            self.assertNotIn("angle", manifest["EM-26078"])
            response = {"custom_id": "EM-26078", "response": {"body": {
                "output_text": "Les cinq numéros occupent 4 dizaines."}}}
            ok, blocked, failed, _, _ = traiter(json.dumps(response), manifest, root / "drafts")
            self.assertEqual((ok, blocked, failed), (1, 0, 0))
            draft = json.loads((root / "drafts" / "EM-26078" / "draft.json").read_text())
            self.assertEqual(draft["draft"]["title"], "EuroMillions — tirage du 29 septembre 2026")
            self.assertNotIn("editorial_angle", draft["draft"])


if __name__ == "__main__":
    unittest.main()


class MultigameAnglePromptTests(unittest.TestCase):
    def test_real_optional_components(self):
        from editorial_angle import build_prompt
        for draw_id in ('LO-20261007', 'KE-26372', 'EM-26081'):
            source, _ = facts_for(draw_id)
            payload = json.loads(build_prompt(source).split('TIRAGE ET FAITS VÉRIFIÉS :\n')[1])
            self.assertEqual(payload['game_id'], source['game_id'])
            self.assertEqual(payload['main'], source['main'])
            self.assertEqual('stars' in payload, 'stars' in source)
            if source['game_id'] == 'loto':
                self.assertEqual(payload['chance'], [8])
