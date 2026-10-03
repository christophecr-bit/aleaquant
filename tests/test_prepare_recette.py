"""Snapshots recette : copie isolée, exclusions, sécurité et traçabilité.

Auteur : AleaQuant · Date : 2026-10-03 · Version : 1.1.
Historique : 1.0 snapshots isolés; 1.1 adaptation des liens internes HTML.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_recette", ROOT / "tools/prepare_recette.py")
recette = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recette)


def config(path):
    return json.loads("\n".join(line for line in path.read_text().splitlines()
                               if not line.lstrip().startswith("//")))


class PrepareRecetteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.output = self.root / "snapshot"
        files = {".assetsignore": "# Faits locaux\ndata/facts/**\n",
                 "_headers": "/*\n  Content-Security-Policy: default-src 'self'\n  X-Frame-Options: DENY\n",
                 "robots.txt": "User-agent: *\nAllow: /\n",
                 "index.html": "<h1>Recette</h1>",
                 "maquette/index.html": "<h1>Maquette</h1>",
                 "data/facts/secret.json": '{"local": true}',
                 "data/draws.json": '{"rows": []}'}
        for name, content in files.items():
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        self.state = {"head": "abc123", "dirty": True,
                      "status_porcelain": [" M dist/index.html"]}
        self.mock = patch.object(recette, "git_state", return_value=self.state)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def prepare(self, **kwargs):
        return recette.prepare(self.source, self.output, **kwargs)

    def test_snapshot_isole_exclut_faits_et_preserve_sources_et_production(self):
        original = {p.relative_to(self.source): p.read_bytes()
                    for p in self.source.rglob("*") if p.is_file()}
        prod_before = (ROOT / "wrangler.jsonc").read_bytes()
        manifest = self.prepare()
        self.assertFalse((self.output / "dist/data/facts").exists())
        self.assertEqual((self.output / "dist/data/draws.json").read_bytes(),
                         original[Path("data/draws.json")])
        self.assertEqual({p.relative_to(self.source): p.read_bytes()
                          for p in self.source.rglob("*") if p.is_file()}, original)
        self.assertEqual((ROOT / "wrangler.jsonc").read_bytes(), prod_before)
        self.assertEqual(manifest["asset_count"], 4)
        self.assertEqual(manifest["git"], self.state)
        self.assertTrue((self.output / "manifest.json").is_file())
        self.assertFalse((self.output / "dist/manifest.json").exists())

    def test_noindex_global_conserve_entetes_securite(self):
        self.prepare()
        headers = (self.output / "dist/_headers").read_text()
        self.assertIn("/*\n  X-Robots-Tag: noindex, nofollow, noarchive\n", headers)
        self.assertIn("Content-Security-Policy: default-src 'self'", headers)
        self.assertIn("X-Frame-Options: DENY", headers)
        self.assertEqual((self.output / "dist/robots.txt").read_text(),
                         "User-agent: *\nDisallow: /\n")

    def test_manifeste_identifie_contenu_exact_et_adaptations(self):
        manifest = self.prepare()
        for entry in manifest["files"]:
            data = (self.output / "dist" / entry["path"]).read_bytes()
            self.assertEqual(entry["sha256"], recette.sha256(data))
            self.assertEqual(entry["bytes"], len(data))
            self.assertEqual(entry["source_sha256"],
                             recette.sha256((self.source / entry["path"]).read_bytes()))
        self.assertEqual(len(manifest["public_content_sha256"]), 64)

    def test_regle_ignore_inconnue_refusee(self):
        (self.source / ".assetsignore").write_text("data/facts/**\nprivate/**\n")
        with self.assertRaisesRegex(ValueError, "non prises en charge"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_faits_non_exclus_refuses(self):
        (self.source / ".assetsignore").write_text("# aucune exclusion\n")
        with self.assertRaisesRegex(ValueError, "obligatoire"):
            self.prepare()

    def test_budget_depasse_refuse_sans_snapshot(self):
        with self.assertRaisesRegex(ValueError, "Budget assets"):
            self.prepare(asset_limit=3)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".preparing-*")))

    def test_snapshot_existant_ne_peut_pas_etre_ecrase(self):
        self.prepare()
        manifest = (self.output / "manifest.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "déjà présent"):
            self.prepare()
        self.assertEqual((self.output / "manifest.json").read_bytes(), manifest)

    def test_lien_symbolique_et_destination_dans_source_refuses(self):
        with self.assertRaisesRegex(ValueError, "destination"):
            recette.prepare(self.source, self.source / "snapshot")
        (self.source / "link.html").symlink_to(self.source / "index.html")
        with self.assertRaisesRegex(ValueError, "Lien symbolique"):
            self.prepare()

    def test_changement_git_pendant_copie_refuse(self):
        with patch.object(recette, "git_state", side_effect=[self.state, {**self.state, "head": "def456"}]):
            with self.assertRaisesRegex(ValueError, "État Git modifié"):
                self.prepare()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".preparing-*")))

    def test_source_changee_pendant_copie_refusee(self):
        write_bytes = Path.write_bytes

        def change_source(target, data):
            result = write_bytes(target, data)
            if target.name == "index.html" and target.parent.name == "dist":
                (self.source / "index.html").write_text("modifié pendant copie")
            return result

        with patch.object(Path, "write_bytes", change_source):
            with self.assertRaisesRegex(ValueError, "Source modifiée"):
                self.prepare()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".preparing-*")))

    def test_liens_internes_seuls_adaptes_sans_reserialiser_html(self):
        source = '''<!doctype html>
<link rel="canonical" href="https://aleaquant.org/maquette/">
<a class="test" href="https://aleaquant.aleaquant.workers.dev/tirages/?a=1&amp;b=2#sommes">Voir</a>
<A HREF='https://aleaquant.org/atlas/#details'>Atlas</A>
<a href=//aleaquant.org/journal/>Journal</a>
<a href="https://aleaquant.org">Accueil</a>
<a href="https://example.org/">Externe</a>
<a href="https://aleaquant.org.example.org/">Autre</a>
<a href="https://aleaquant.org@evil.example/">Autre</a>
<a href="/deja-relatif/">Relatif</a>
<p>https://aleaquant.org/ texte</p>
<script>const link = '<a href="https://aleaquant.org/script/">';</script>
<!-- <a href="https://aleaquant.org/comment/"> -->
<a data-note='texte href="https://aleaquant.org/faux/"' href="https://aleaquant.org/vrai/">Vrai</a>
'''
        expected = source.replace('href="https://aleaquant.aleaquant.workers.dev/tirages/?a=1&amp;b=2#sommes"',
                                  'href="/tirages/?a=1&amp;b=2#sommes"')
        expected = expected.replace("HREF='https://aleaquant.org/atlas/#details'", "HREF='/atlas/#details'")
        expected = expected.replace('href=//aleaquant.org/journal/', 'href=/journal/')
        expected = expected.replace('href="https://aleaquant.org">', 'href="/">')
        expected = expected.replace('href="https://aleaquant.org/vrai/"', 'href="/vrai/"')
        self.assertEqual(recette.recette_links(source.encode()).decode(), expected)

    def test_overlay_liens_dans_copie_seulement_et_manifeste(self):
        source = b'<a href="https://aleaquant.aleaquant.workers.dev/tirages/">Tirages</a>'
        (self.source / 'maquette/index.html').write_bytes(source)
        manifest = self.prepare()
        self.assertEqual((self.source / 'maquette/index.html').read_bytes(), source)
        self.assertEqual((self.output / 'dist/maquette/index.html').read_bytes(),
                         b'<a href="/tirages/">Tirages</a>')
        self.assertTrue(any('href' in item for item in manifest['overlays']))

    def test_config_recette_distincte_de_production(self):
        prod = config(ROOT / "wrangler.jsonc")
        stage = config(ROOT / "wrangler.recette.jsonc")
        self.assertEqual(prod["name"], "aleaquant")
        self.assertEqual(prod["routes"], [{"pattern": "aleaquant.org", "custom_domain": True}])
        self.assertEqual(stage["name"], "aleaquant-recette")
        self.assertEqual(stage["assets"]["directory"], "./.recette/current/dist")
        self.assertFalse(stage["workers_dev"])
        self.assertFalse(stage["preview_urls"])
        self.assertEqual(stage["routes"], [{"pattern": "recette.aleaquant.org", "custom_domain": True}])


if __name__ == "__main__":
    unittest.main()
