"""Tests de transport/import éditorial, y compris l'identité des titres de tirage.

Nom : tests/test_import.py · v0.2 · 2026-10-02 · Auteur : AleaQuant
Historique : vérifie la présence du jeu et de la date complète dans les titres publiés.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('import_article',Path(__file__).resolve().parents[1]/'scripts/import_article.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ImportTests(unittest.TestCase):
    def article(self):
        pack={'evidence':[]}
        draft={'title':'Test','body':'Test de transport','claims':[{'text':'Test'}],'research_pack_sha256':module.digest(pack)}
        sha=module.digest(draft)
        return {'schema':'aleaquant-article-v1','status':'HUMAN_APPROVED','article_id':'test-1','draft':draft,'draft_sha256':sha,'research_pack':pack,'human_decision':{'approved':True,'reviewer':'Test','draft_sha256':sha}}
    def test_tampered_body_rejected(self):
        article=self.article();article['draft']['body']+=' changement'
        with self.assertRaises(ValueError):module.validate(article)
    def test_pending_rejected(self):
        article=self.article();article['status']='READY_FOR_HUMAN'
        with self.assertRaises(ValueError):module.validate(article)
    def test_tampered_evidence_rejected(self):
        article=self.article();article['research_pack']['evidence'].append('changed')
        with self.assertRaises(ValueError):module.validate(article)
    def test_reimport_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'export.json';target=Path(folder)/'articles.json'
            source.write_text(json.dumps(self.article()))
            module.import_article(source,target);module.import_article(source,target)
            self.assertEqual(len(json.loads(target.read_text())['articles']),1)
    def test_draw_report_must_match_draw_id(self):
        article = self.article()
        article['kind'] = 'draw_report'
        article['research_pack']['draw_id'] = 'EM-2011053'
        article['draft']['research_pack_sha256'] = module.digest(article['research_pack'])
        article['draft_sha256'] = module.digest(article['draft'])
        article['human_decision']['draft_sha256'] = article['draft_sha256']
        with self.assertRaisesRegex(ValueError, 'non concordants'):
            module.validate(article)

    def test_draw_title_names_game_and_complete_date(self):
        article = self.article()
        article['kind'] = 'draw_report'
        article['article_id'] = 'tirage-EM-2011053'
        article['research_pack']['draw_id'] = 'EM-2011053'
        article['draft']['title'] = 'Une somme à 222'
        article['draft']['research_pack_sha256'] = module.digest(article['research_pack'])
        article['draft_sha256'] = module.digest(article['draft'])
        article['human_decision']['draft_sha256'] = article['draft_sha256']
        with self.assertRaisesRegex(ValueError, 'nommer explicitement le jeu'):
            module.validate(article)
        article['draft']['title'] = 'EuroMillions — tirage du 6 septembre 2011 : une somme à 222'
        article['draft_sha256'] = module.digest(article['draft'])
        article['human_decision']['draft_sha256'] = article['draft_sha256']
        self.assertIs(module.validate(article), article)

    def test_one_article_per_draw(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'export.json'
            target = Path(folder) / 'articles.json'
            article = self.article()
            article['kind'] = 'draw_report'
            article['article_id'] = 'tirage-EM-2011053'
            article['research_pack']['draw_id'] = 'EM-2011053'
            article['draft']['title'] = 'EuroMillions — tirage du 6 septembre 2011'
            article['draft']['research_pack_sha256'] = module.digest(article['research_pack'])
            article['draft_sha256'] = module.digest(article['draft'])
            article['human_decision']['draft_sha256'] = article['draft_sha256']
            source.write_text(json.dumps(article))
            target.write_text(json.dumps({'schema': 'aleaquant-journal-v1', 'articles': [{
                'kind': 'draw_report', 'article_id': 'old-id',
                'research_pack': {'draw_id': 'EM-2011053'}
            }]}))
            with self.assertRaisesRegex(ValueError, 'déjà associé'):
                module.import_article(source, target)

if __name__=='__main__':unittest.main()
