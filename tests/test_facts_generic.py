"""Faits génériques : équivalence avec EuroMillions publié, et règles propres aux autres jeux."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
STORE = ROOT.parent / 'aleaquant-data' / 'data' / 'aleaquant.sqlite3'
FAITS = ROOT / 'dist' / 'data' / 'facts'


def faits(did):
    return json.loads((FAITS / f'{did}.json').read_text(encoding='utf-8'))


def fait(corps, fact_id):
    return next(f for f in corps['facts'] if f['fact_id'] == fact_id)


@unittest.skipUnless(STORE.exists(), 'journal aleaquant-data absent')
class EquivalenceEuroMillionsTests(unittest.TestCase):
    def test_composante_principale_identique_aux_faits_publies(self):
        """39 700 faits main.* : même classe, probabilité, queue, rareté, historique, énoncé."""
        from facts_generic import construire_faits
        gen = construire_faits('euromillions')
        champs = ('value', 'class_size', 'domain_size', 'p_class', 'rarity', 'p_le', 'p_ge',
                  'tail', 'historical_prior', 'statement')
        compares = 0
        for did, g in gen.items():
            ref = {f['fact_id']: f for f in faits(did)['facts']}
            for f in g['facts']:
                if f['fact_id'].startswith('F.main.'):
                    for c in champs:
                        self.assertEqual(f.get(c), ref[f['fact_id']].get(c), f"{did}/{f['fact_id']}/{c}")
                    compares += 1
        self.assertGreater(compares, 39000)


class LotoTests(unittest.TestCase):
    def setUp(self):
        if not (FAITS / 'LO-20260928.json').exists():
            self.skipTest('faits Loto non générés')

    def test_probabilite_formule_actuelle(self):
        """5 numéros sur 49 et 1 numéro chance sur 10 : 1 sur 19 068 840."""
        f = fait(faits('LO-20260928'), 'F.grid.probability')
        self.assertEqual(f['value']['full_combinations'], 19068840)

    def test_complementaire_hors_de_la_grille(self):
        """Tirée mais jamais cochée : 1 sur C(49,6), et non C(49,6) × 43."""
        corps = faits('LO-19960615-2')
        f = fait(corps, 'F.grid.probability')
        self.assertEqual(f['value']['full_combinations'], 13983816)
        self.assertNotIn('complementaire', f['value']['grid'])
        self.assertIn('complementaire', corps['components'])

    def test_premier_tirage_d_une_formule_sans_passe(self):
        """Le premier tirage à 5 numéros n'a AUCUN tirage antérieur comparable : les
        4 858 tirages à 6 numéros qui le précèdent ne comptent pas."""
        corps = faits('LO-20081006')
        self.assertEqual(corps['rule_id'], 'loto-49-5-chance-v1')
        self.assertEqual(corps['prior_draws'], 0)
        for f in corps['facts']:
            # AleaQuant · 2026-10-02 : un profil descriptif n'a ni loi ni historique.
            if f.get('category') == 'descriptive_profile':
                self.assertNotIn('historical_prior', f)
                self.assertNotIn('rarity', f)
                self.assertNotIn('p_class', f)
            elif f.get('metric', '').startswith('main.'):
                self.assertEqual(f['historical_prior']['draws'], 0, f['fact_id'])

    def test_pas_de_fait_de_forme_sur_un_numero_seul(self):
        """Le numéro chance est uniforme : sa « rareté » ne porte aucune information."""
        corps = faits('LO-20260928')
        self.assertFalse([f for f in corps['facts'] if f.get('metric', '').startswith('chance.')])

    def test_deux_tirages_le_meme_jour_ordonnes(self):
        """Le second tirage d'une journée compte le premier parmi ses antérieurs."""
        premier, second = faits('LO-19960615-1'), faits('LO-19960615-2')
        self.assertEqual(second['prior_draws'], premier['prior_draws'] + 1)


class ProfilsParRegimeTests(unittest.TestCase):
    def test_deux_regimes_separes(self):
        chemin = ROOT / 'dist' / 'data' / 'rarity_profiles' / 'loto.json'
        if not chemin.exists():
            self.skipTest('profils Loto non générés')
        regimes = json.loads(chemin.read_text(encoding='utf-8'))['regimes']
        self.assertEqual(set(regimes), {'main-5-49', 'main-6-49'})
        # la rareté structurelle de sorted_gaps se retrouve dans les deux formules
        for r in regimes.values():
            self.assertTrue(r['main.sorted_gaps']['constant'])


if __name__ == '__main__':
    unittest.main()
