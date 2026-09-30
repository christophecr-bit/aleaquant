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
from guards import (  # noqa: E402
    RARITY_PROFILES, guard_class_citations, guard_enum_leak,
    guard_interpretive_words, guard_markdown, notable_badges, notable_level,
    paragraph_evidence, strip_markdown,
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


sys.path.insert(0, str(ROOT / 'tools'))
from lint_language import INTERDITES, LEGITIMES, lint as lint_language  # noqa: E402


class LinterTests(unittest.TestCase):
    """Chantier D3 : la ligne éditoriale doit être un test qui échoue."""

    def test_phrases_interdites_refusees(self):
        for phrase in INTERDITES:
            self.assertTrue(lint_language(phrase), f"non refusée : {phrase}")

    def test_phrases_legitimes_acceptees(self):
        for phrase in LEGITIMES:
            self.assertEqual(lint_language(phrase), [], f"faux positif : {phrase}")

    def test_article_publie_conforme(self):
        journal = json.loads((ROOT / 'dist' / 'articles.json').read_text(encoding='utf-8'))
        for a in journal['articles']:
            self.assertEqual(lint_language(a['draft']['body']), [], a['article_id'])

    def test_import_refuse_un_vocabulaire_interdit(self):
        """Le linter doit bloquer l'import, pas seulement avertir."""
        import importlib.util
        spec = importlib.util.spec_from_file_location('ia', ROOT / 'scripts' / 'import_article.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        pack = {'evidence': []}
        draft = {'title': 'T', 'body': 'Le 42 va sortir au prochain tirage.',
                 'claims': [{'text': 'x'}], 'research_pack_sha256': m.digest(pack)}
        sha = m.digest(draft)
        article = {'schema': 'aleaquant-article-v1', 'status': 'HUMAN_APPROVED',
                   'article_id': 'test-lint', 'draft': draft, 'draft_sha256': sha,
                   'research_pack': pack,
                   'human_decision': {'approved': True, 'reviewer': 'T', 'draft_sha256': sha}}
        with self.assertRaises(ValueError):
            m.validate(article)


class BadgeTests(unittest.TestCase):
    """Les puces de rareté sont calculées côté Python, jamais rédigées par le modèle,
    et n'apparaissent que pour une mesure au-dessus de sa propre référence."""

    def test_aucune_puce_sur_un_tirage_ordinaire(self):
        """EM-26077 et EM-2004010 n'ont aucune mesure au-dessus de sa référence."""
        for draw in ('EM-26077', 'EM-2004010'):
            self.assertEqual(notable_badges(facts(draw)), [], draw)

    def test_puces_sur_un_tirage_remarquable(self):
        b = notable_badges(facts('EM-2011053'))
        self.assertTrue(b)
        self.assertIn('F.main.sum', [x['fact_id'] for x in b])

    def test_jamais_de_mesure_a_rarete_constante(self):
        """sorted_gaps est très rare pour tout tirage : jamais de puce dessus."""
        for draw in ('EM-2011053', 'EM-26077'):
            metriques = [x['metric'] for x in notable_badges(facts(draw))]
            self.assertNotIn('main.sorted_gaps', metriques)
            self.assertNotIn('stars.sum', metriques)

    def test_pas_de_doublon_redondant(self):
        """span et mean_gap portent la même information : une seule puce."""
        metriques = [x['metric'] for x in notable_badges(facts('EM-2011053'))]
        self.assertFalse('main.span' in metriques and 'main.mean_gap' in metriques)

    def test_plafonnees_a_cinq(self):
        self.assertLessEqual(len(notable_badges(facts('EM-2011053'))), 5)

    def test_niveau_est_une_classe_css_valide(self):
        for x in notable_badges(facts('EM-2011053')):
            self.assertIn(x['niveau'], ('COMMON', 'UNCOMMON', 'RARE', 'VERY_RARE'))


class MarkdownTests(unittest.TestCase):
    """dist/app.js affiche le corps avec textContent (jamais innerHTML, par sécurité) :
    un « ** » du modèle s'affiche donc littéralement sur le site."""

    def test_gras_retire(self):
        t = 'la **Somme** vaut 222 en **classe très rare**'
        self.assertEqual(strip_markdown(t), 'la Somme vaut 222 en classe très rare')

    def test_garde_detecte_les_marqueurs(self):
        self.assertEqual(guard_markdown('la **Somme**'), ['**'])
        self.assertEqual(guard_markdown('la Somme'), [])

    def test_texte_sans_markdown_intact(self):
        t = "La répartition 0-0-0-1-4 et l'étendue 15, de 35 à 50."
        self.assertEqual(strip_markdown(t), t)

    def test_chiffres_preserves(self):
        """Le nettoyage ne doit toucher aucun nombre."""
        from guards import normalize_numbers
        t = 'somme **222**, classe de **141** sur **2 118 760**'
        self.assertEqual(normalize_numbers(strip_markdown(t)), normalize_numbers(t))


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

    def test_faits_non_metriques_attribues(self):
        """La probabilité de la combinaison complète, la signature et l'historique
        exact n'ont pas de champ metric : ils étaient ignorés, donc le premier
        paragraphe d'un article n'avait aucun fait attribué."""
        f = facts('EM-2011053')
        para = ("le 6 septembre 2011, la combinaison avait une probabilité de "
                "1 sur 116 531 800 sous la règle alors en vigueur")
        self.assertIn('F.grid.probability', paragraph_evidence(para, f))
        para2 = "ces cinq numéros n'étaient jamais sortis ensemble auparavant"
        self.assertIn('F.history.exact_main', paragraph_evidence(para2, f))

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
