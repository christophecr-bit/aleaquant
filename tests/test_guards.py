"""Régression sur les gardes de l'agent éditorial.

Bug d'origine : guard_interpretive_words() comparait les mots de rareté au MAXIMUM
de rareté de l'ensemble des faits. Comme main.sorted_gaps est VERY_RARE pour les 1984
tirages de l'historique, ce maximum valait toujours VERY_RARE et le garde ne pouvait
JAMAIS se déclencher — il affichait OK sur tous les articles sans rien vérifier.

Le correctif ne compte que les faits dépassant la référence de leur propre mesure
(dist/data/rarity_profiles.json). Ces tests échouent si la régression revient.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agent'))
from llm_compose_test import (  # noqa: E402
    RARITY_PROFILES, guard_class_citations, guard_enum_leak,
    guard_interpretive_words, notable_level, paragraph_evidence,
)


def facts(draw_id):
    return json.loads((ROOT / 'dist' / 'data' / 'facts' / f'{draw_id}.json').read_text(encoding='utf-8'))


class ProfileTests(unittest.TestCase):
    def test_profils_charges(self):
        self.assertGreater(len(RARITY_PROFILES), 20, 'rarity_profiles.json absent — '
                           'lancer python3 engine/rarity_profiles.py')

    def test_sorted_gaps_marque_non_informatif(self):
        """La mesure qui a cassé le garde doit rester marquée comme constante."""
        prof = RARITY_PROFILES['main.sorted_gaps']
        self.assertTrue(prof['constant'])
        self.assertEqual(prof['baseline'], 'VERY_RARE')
        self.assertFalse(prof['informative'])

    def test_fait_constant_jamais_notable(self):
        for f in facts('EM-2011053')['facts']:
            if f.get('metric') == 'main.sorted_gaps':
                self.assertIsNone(notable_level(f), 'sorted_gaps ne doit jamais être notable')


class LexicalGuardTests(unittest.TestCase):
    def test_le_garde_se_declenche_sur_un_tirage_ordinaire(self):
        """EM-2004010 n'a aucune mesure au-dessus de sa référence : tout mot de
        rareté doit être signalé. C'est le test que l'ancien garde ne passait pas."""
        problemes = guard_interpretive_words('Une forme exceptionnelle, avec un écart rare.',
                                            facts('EM-2004010'))
        mots = {w for w, _ in problemes}
        self.assertIn('exceptionnelle', mots)
        self.assertIn('rare', mots)

    def test_mot_legitime_accepte(self):
        """EM-2011053 a une somme très rare au-dessus de sa référence : le mot passe."""
        self.assertEqual(guard_interpretive_words('Une somme exceptionnelle.', facts('EM-2011053')), [])

    def test_negation_ignoree(self):
        self.assertEqual(guard_interpretive_words("Ce n'est pas une forme rare.",
                                                  facts('EM-2004010')), [])

    def test_frontieres_de_mot(self):
        """« rareté » et « VERY_RARE » ne sont pas des affirmations de rareté."""
        f = facts('EM-2004010')
        self.assertEqual(guard_interpretive_words('Sa rareté se discute.', f), [])
        self.assertEqual(guard_interpretive_words('Profil VERY_RARE.', f), [])


class AttributionTests(unittest.TestCase):
    """L'appariement paragraphe -> fait doit rester précis. Une première version
    attribuait 20 faits à un paragraphe parce qu'une valeur comme « 2 » ou « 4 »
    apparaît dans presque toutes les mesures : une attribution qui désigne tout ne
    désigne rien."""

    def test_attribution_precise(self):
        f = facts('EM-2011053')
        para = ("la somme vaut 222, ce qui la place dans une classe de 141 sur "
                "2 118 760, avec une queue de 0,04 %")
        self.assertEqual(paragraph_evidence(para, f), ['F.main.sum'])

    def test_valeur_seule_ne_suffit_pas(self):
        """« 2 » sans nom de mesure ne doit attribuer aucun fait."""
        f = facts('EM-2011053')
        self.assertEqual(paragraph_evidence('Il y a 2 choses à noter ici.', f), [])

    def test_nom_et_valeur_attribuent(self):
        f = facts('EM-2011053')
        self.assertIn('F.main.span', paragraph_evidence("l'étendue vaut 15", f))

    def test_domaine_non_distinctif(self):
        """2 118 760 est commun à tous les faits : il ne doit rien attribuer seul."""
        f = facts('EM-2011053')
        self.assertEqual(paragraph_evidence('sur 2 118 760 combinaisons possibles', f), [])


class OtherGuardTests(unittest.TestCase):
    def test_effectifs_faux_detectes(self):
        f = facts('EM-2011053')
        self.assertEqual(guard_class_citations('classe de 141 sur 2 118 760', f), [])
        self.assertTrue(guard_class_citations('classe de 142 sur 2 118 760', f))
        self.assertTrue(guard_class_citations('une queue de 9,9 %', f))

    def test_noms_de_code_detectes(self):
        self.assertEqual(guard_enum_leak('classe très rare'), [])
        self.assertEqual(guard_enum_leak('classée VERY_RARE'), ['VERY_RARE'])


if __name__ == '__main__':
    unittest.main()
