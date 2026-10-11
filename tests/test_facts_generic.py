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
        """Tous les facts publiés restent identiques, hors profil descriptif ajouté après coup."""
        from facts_generic import construire_faits
        gen = construire_faits('euromillions')
        files = list(FAITS.glob('EM-*.json'))
        self.assertEqual(set(gen), {p.stem for p in files})
        compares = 0
        for did, g in gen.items():
            old = faits(did)
            # F.main.decade_sums was added locally after these approved facts were built.
            # The page has a deterministic fallback, so parity does not rewrite old SHAs.
            old['facts'] = [f for f in old['facts']
                            if f.get('fact_id') != 'F.main.decade_sums']
            expected = dict(g)
            expected['facts'] = [f for f in expected['facts']
                                 if f.get('fact_id') != 'F.main.decade_sums']
            self.assertEqual(json.dumps(expected, sort_keys=True, ensure_ascii=False),
                             json.dumps(old, sort_keys=True, ensure_ascii=False), did)
            compares += len(g['facts'])
            profile = fait(g, 'F.main.decade_sums')['value']['profile']
            self.assertEqual(len(profile), 5)
        self.assertGreater(compares, 50000)


class LotoTests(unittest.TestCase):
    def setUp(self):
        if not (FAITS / 'LO-20260928.json').exists():
            self.skipTest('faits Loto non générés')

    def test_probabilite_formule_actuelle(self):
        """5 numéros sur 49 et 1 numéro chance sur 10 : 1 sur 19 068 840."""
        f = fait(faits('LO-20260928'), 'F.grid.probability')
        self.assertEqual(f['value']['full_combinations'], 19068840)

    def test_fait_somme_par_dizaine(self):
        """La nouvelle décomposition est construite pour la règle Loto 5/49."""
        from unittest.mock import patch
        from facts_generic import construire_faits

        draw = {
            'draw_id': 'LO-SUM-DECADE', 'occurred_on': '2026-10-02', 'session': None,
            'rule_id': 'loto-49-5-chance-v1',
            'values': [['main', [2, 30, 36, 44, 48]], ['chance', [9]]],
            'source': {'publisher': 'FDJ', 'source_id': 'LO-SUM-DECADE'},
            'revision': 1, 'sha256': 'test-sha',
        }
        with patch('facts_generic.charger_tirages', return_value=[draw]):
            facts = construire_faits('loto')['LO-SUM-DECADE']
        profile = fait(facts, 'F.main.decade_sums')['value']['profile']
        self.assertEqual([(b['count'], b['sum']) for b in profile],
                         [(1, 2), (0, 0), (1, 30), (1, 36), (2, 92)])

    def test_template_ne_traite_pas_le_profil_descriptif_comme_rarete(self):
        sys.path.insert(0, str(ROOT / 'agent'))
        from draw_report import select

        profile = {'fact_id': 'F.main.decade_sums', 'metric': 'main.decade_sums',
                   'category': 'descriptive_profile', 'value': {'profile': []}}
        self.assertEqual(select({'facts': [profile]}), ([], []))

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


class KenoTests(unittest.TestCase):
    def test_tirage_exact_distinct_de_la_probabilite_d_une_grille(self):
        from math import comb
        from unittest.mock import patch
        from facts_generic import construire_faits

        def tirage(did, date, session, rule, count, domain):
            return {
                'draw_id': did, 'occurred_on': date, 'session': session,
                'rule_id': rule, 'values': [['main', list(range(1, count + 1))]],
                'source': {'publisher': 'FDJ', 'source_id': did},
                'revision': 1, 'sha256': did,
            }

        old = 'keno-70-20-v1'
        current = 'keno-56-16-v1'
        draws = [
            tirage('KE-OLD-1', '2025-11-02', 'midi', old, 20, 70),
            tirage('KE-OLD-2', '2025-11-02', 'soir', old, 20, 70),
            tirage('KE-NEW-1', '2025-11-03', None, current, 16, 56),
            tirage('KE-NEW-2', '2025-11-04', None, current, 16, 56),
        ]
        with patch('facts_generic.charger_tirages', return_value=draws):
            result = construire_faits('keno')

        for did, total, rule in (
            ('KE-OLD-1', comb(70, 20), old),
            ('KE-NEW-1', comb(56, 16), current),
        ):
            corps = result[did]
            f = fait(corps, 'F.draw.probability')
            self.assertEqual(f['category'], 'exact_draw')
            self.assertEqual(f['value']['full_draws'], total)
            self.assertEqual(f['value']['rule_id'], rule)
            self.assertNotIn('F.grid.probability', [x['fact_id'] for x in corps['facts']])
            self.assertIn('ne donne pas la probabilité de gain', f['statement'])
            self.assertEqual(corps['source']['revision_sha256'], did)
            picks, domain = f['value']['draw']['main'].values()
            law_path = ROOT / 'dist' / 'data' / 'laws' / f'regime-{picks}-{domain}.json'
            law = json.loads(law_path.read_text(encoding='utf-8'))
            missing = set(law['missing_fields'])
            metrics = {x['metric'].split('.', 1)[1] for x in corps['facts']
                       if x.get('category') == 'class_metric' and 'metric' in x}
            self.assertTrue(missing.isdisjoint(metrics))
            self.assertEqual(metrics, set(law['laws']))
            profile = fait(corps, 'F.main.decade_sums')
            self.assertEqual(profile['category'], 'descriptive_profile')
            self.assertNotIn('rarity', profile)

        self.assertEqual(result['KE-OLD-1']['prior_draws'], 0)
        self.assertEqual(result['KE-OLD-2']['prior_draws'], 1)
        self.assertEqual(result['KE-NEW-1']['prior_draws'], 0)
        self.assertEqual(result['KE-NEW-2']['prior_draws'], 1)
        same_metric = fait(result['KE-OLD-2'], 'F.main.sum')
        self.assertEqual(same_metric['historical_prior']['count'], 1)
        self.assertEqual(fait(result['KE-NEW-1'], 'F.main.sum')['historical_prior']['count'], 0)
        old_profile = fait(result['KE-OLD-1'], 'F.main.decade_sums')['value']['profile']
        current_profile = fait(result['KE-NEW-1'], 'F.main.decade_sums')['value']['profile']
        self.assertEqual([(b['count'], b['sum']) for b in old_profile[:2]], [(10, 55), (10, 155)])
        self.assertEqual([(b['count'], b['sum']) for b in current_profile[:2]], [(10, 55), (6, 81)])


class EcritureSelectiveTests(unittest.TestCase):
    def test_selection_reproductible_et_id_inconnu_refuse(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from facts_generic import ecrire

        corps = {'schema': 'aleaquant-draw-facts-v1', 'draw_id': 'KE-TEST', 'facts': []}
        with TemporaryDirectory() as tmp:
            dossier = Path(tmp)
            with patch('facts_generic.construire_faits', return_value={'KE-TEST': corps}) as build:
                self.assertEqual(ecrire('keno', dossier, seulement={'KE-TEST'}), 1)
                premier = (dossier / 'KE-TEST.json').read_bytes()
                self.assertEqual(ecrire('keno', dossier, seulement={'KE-TEST'}), 1)
                self.assertEqual((dossier / 'KE-TEST.json').read_bytes(), premier)
                build.assert_called_with('keno', store=STORE, seulement={'KE-TEST'})
                with self.assertRaisesRegex(ValueError, 'KE-ABSENT'):
                    ecrire('keno', dossier, seulement={'KE-ABSENT'})
            self.assertEqual([p.name for p in dossier.iterdir()], ['KE-TEST.json'])

    def test_sha_source_identique_preserve_le_fichier_deja_reference(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from facts_generic import ecrire

        with TemporaryDirectory() as temp:
            dossier = Path(temp)
            cible = dossier / 'EM-test.json'
            ancien = {'schema': 'aleaquant-draw-facts-v1', 'draw_id': 'EM-test',
                      'source': {'revision_sha256': 'same-sha'}, 'facts': []}
            nouveau = dict(ancien, engine='nouveau', facts=[{'fact_id': 'nouveau'}])
            cible.write_text(json.dumps(ancien), encoding='utf-8')
            with patch('facts_generic.construire_faits', return_value={'EM-test': nouveau}), \
                 patch('facts_generic.charger_tirages', return_value=[{'draw_id': 'EM-other'}]):
                self.assertEqual(ecrire('euromillions', dossier, seulement={'EM-test'}), 0)
            self.assertEqual(json.loads(cible.read_text(encoding='utf-8')), ancien)


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
