"""Témoins de review — v1.0, 2026-10-02, Auteur : AleaQuant.
Historique : C2/C5, fuite des consignes, notes liées au SHA, absence de publication.
TODO : enrichir le corpus de paraphrases, sans utiliser d'API dans les tests.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agent'))
from article_traceability import (build_methodology, methodology_html,
                                 validate_traceability, refresh_review_metadata)
from guards import paragraph_evidence, build_compose_article, run_all_guards, evidence_block
from draw_report import digest
from compose_draw_report import compose_prompt

FIXTURES = Path(__file__).parent / 'fixtures/traceability'


class TraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads((FIXTURES / 'EM-26078-facts.json').read_text())
        self.original = json.loads((FIXTURES / 'EM-26078-review.json').read_text())

    def article(self):
        text = "L'étendue vaut 40.\n\nLes étoiles 08 et 11 forment un écart de 3. La somme des étoiles vaut 19."
        return build_compose_article(FIXTURES / 'EM-26078-facts.json', self.facts, text, {})

    def test_c2_ne_cite_plus_la_somme_des_etoiles(self):
        refs = paragraph_evidence(self.original['draft']['claims'][1]['text'], self.facts)
        self.assertIn('F.main.decade_counts', refs)
        self.assertIn('F.main.span', refs)
        self.assertNotIn('F.stars.sum', refs)

    def test_c5_cite_ecart_et_somme_des_etoiles(self):
        refs = paragraph_evidence(self.original['draft']['claims'][4]['text'], self.facts)
        self.assertEqual(set(refs), {'F.stars.gap', 'F.stars.sum'})

    def test_original_refuse_meme_avec_gardes_verts(self):
        issues = validate_traceability(self.original, self.facts)
        self.assertTrue(any('C2' in i for i in issues))
        self.assertTrue(any('C5' in i for i in issues))
        self.assertTrue(any('Comparaison' in i for i in issues))
        self.assertTrue(any('Mode' in i for i in issues))

    def test_paragraphe_editorial_sans_claim_impose(self):
        a = build_compose_article(FIXTURES / 'EM-26078-facts.json', self.facts,
                                  "Prenons le temps de lire ces mesures.\n\nL'étendue vaut 40.", {})
        self.assertEqual(a['status'], 'PENDING_HUMAN')
        self.assertEqual(len(a['draft']['claims']), 1)

    def test_nombre_present_ailleurs_ne_suffit_pas(self):
        a = self.article()
        a['draft']['body'] = "L'étendue vaut 98."
        refresh_review_metadata(a, self.facts)
        self.assertEqual(a['status'], 'BLOCKED')
        self.assertTrue(any('preuves citées' in x for x in a['guard']['problems']))

    def test_source_pas_un_sac_de_petits_nombres(self):
        self.assertEqual(paragraph_evidence('Il y a 3 observations et 19 choses.', self.facts), [])

    def test_prose_libre_possible_mais_claim_hors_registre_bloque(self):
        a = self.article()
        a['draft']['body'] += '\n\nPrenons le temps de lire ces mesures.'
        self.assertEqual(validate_traceability(a, self.facts), [])
        a['draft']['body'] += '\n\nLa somme vaut 98.'
        self.assertTrue(any('hors registre' in i for i in validate_traceability(a, self.facts)))

    def test_promesse_dans_corps_sans_claim_bloque(self):
        a = self.article()
        a['draft']['body'] += '\n\nCette méthode garantit un gain au prochain tirage.'
        self.assertTrue(validate_traceability(a, self.facts))

    def test_note_distingue_composantes_et_signale_sources_manquantes(self):
        m = self.article()['draft']['methodology']
        self.assertEqual(m['components'][0]['prior_draws'], [1984])
        self.assertEqual(m['components'][1]['prior_draws'], [1044])
        self.assertEqual(m['components'][1]['domains'], [66])
        self.assertEqual(len(m['limitations']), 2)
        self.assertNotIn('/Users/', json.dumps(m))
        self.assertNotIn('https://www.fdj.fr', json.dumps(m))

    def test_note_et_preuves_modifiees_refusees(self):
        a = self.article()
        self.assertEqual(validate_traceability(a, self.facts), [])
        a['draft']['methodology']['note'] += ' Certifié.'
        self.assertTrue(validate_traceability(a, self.facts))
        a = self.article()
        a['research_pack']['evidence'][0]['claim'] = 'Preuve inventée'
        self.assertTrue(any('altérée' in i for i in validate_traceability(a, self.facts)))

    def test_relecture_invalide_decision_et_change_empreinte(self):
        a = self.article()
        old = a['draft_sha256']
        a['human_decision'] = {'approved': True}
        a['draft']['body'] = "L'étendue vaut 40."
        refresh_review_metadata(a, self.facts)
        self.assertIsNone(a['human_decision'])
        self.assertEqual(a['status'], 'PENDING_HUMAN')
        self.assertNotEqual(a['draft_sha256'], old)
        self.assertEqual(a['draft_sha256'], digest(a['draft']))

    def test_note_html_echappe_et_refuse_url_active(self):
        m = self.article()['draft']['methodology']
        m['note'] = '<script>alert(1)</script>'
        m['source']['url'] = 'javascript:alert(1)'
        out = methodology_html(m)
        self.assertNotIn('<script>', out)
        self.assertNotIn('javascript:', out)
        self.assertIn('<details>', out)

    def test_nouvelle_metrique_transmise_sans_rarete(self):
        sys.path.insert(0, str(ROOT / 'engine'))
        from facts import decade_sums_fact
        facts = copy.deepcopy(self.facts)
        facts['facts'].append(decade_sums_fact(facts['main'], 50))
        prompt = compose_prompt(facts)
        self.assertIn('F.main.decade_sums', prompt)
        row = next(x for x in evidence_block(facts).splitlines() if 'F.main.decade_sums' in x)
        self.assertNotIn('rareté=', row)
        self.assertIn('F.main.decade_sums', paragraph_evidence('Les sommes par dizaine décrivent le profil.', facts))

    def test_fuite_consigne_declenche_reparation(self):
        text = 'La somme se place au-dessus de sa référence classe peu courante.'
        self.assertTrue(run_all_guards(text, self.facts)['interpretation'])
        self.assertNotIn("c'est ici que se trouve l'information", evidence_block(self.facts))

    def test_rarete_des_etoiles_ne_profite_pas_de_celle_des_numeros(self):
        text = 'La somme des cinq numéros vaut 98, classe rare. La somme des étoiles vaut 19, classe peu courante.'
        self.assertTrue(run_all_guards(text, self.facts)['interpretation'])

    def test_metadonnees_modele_batch_coherentes(self):
        a = build_compose_article(FIXTURES / 'EM-26078-facts.json', self.facts,
                                  "L'étendue vaut 40.", {}, mode='batch', model='temoin')
        self.assertEqual(a['draft']['writer'], a['provenance']['writer'])
        self.assertEqual(a['provenance']['model'], 'temoin')
        self.assertEqual(a['provenance']['mode'], 'batch')
