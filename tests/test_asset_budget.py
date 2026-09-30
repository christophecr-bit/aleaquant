"""Le site statique doit rester dans la limite d'assets du Worker gratuit."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
LIMIT = 20_000


class AssetBudgetTest(unittest.TestCase):
    def test_facts_intermediaires_sont_exclus_du_deploiement(self):
        ignored = (DIST / '.assetsignore').read_text(encoding='utf-8')
        self.assertIn('data/facts/**', ignored)
        facts = DIST / 'data' / 'facts'
        self.assertTrue(facts.is_dir())
        public = [p for p in DIST.rglob('*') if p.is_file() and facts not in p.parents]
        self.assertLess(len(public), LIMIT,
                        f'{len(public)} assets : réduire les fichiers avant déploiement')


if __name__ == '__main__':
    unittest.main()
