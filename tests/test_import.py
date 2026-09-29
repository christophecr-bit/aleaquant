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

if __name__=='__main__':unittest.main()
