"""Références d'article v1 · 2026-10-10 · AleaQuant.

Vérifie le transport littéral d'une référence vers les deux rendus, son
échappement et l'absence de modification de la version humaine approuvée.
Node utilise un DOM local minimal : aucun navigateur, réseau ou rebuild.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import build_pages  # noqa: E402


NODE_RENDER = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const article = JSON.parse(fs.readFileSync(0, 'utf8'));
const before = JSON.stringify(article);
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.style = {}; this.events = {}; this.value = ''; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return (this.text || '') + this.children.map(c => c.textContent).join(''); }
  set innerHTML(value) { throw Error('Untrusted content inserted as markup'); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.text = ''; this.children = children; }
  addEventListener(type, callback) { this.events[type] = callback; }
  focus() {}
  scrollIntoView() {}
}
const elements = new Map();
const document = {
  querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, new Element('div'));
    return elements.get(selector);
  },
  querySelectorAll() { return []; },
  createElement(tag) { return new Element(tag); },
  createTextNode(text) { const node = new Element('#text'); node.textContent = text; return node; }
};
function codes(node) { return [...(node.tag === 'code' ? [node.textContent] : []), ...node.children.flatMap(codes)]; }
const context = vm.createContext({document, URL, fetch: async path => ({ok: true,
  json: async () => path === 'articles.json' ? {articles: [article]} : []})});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
setImmediate(() => {
  const cards = elements.get('#articles');
  if (cards.children.length !== 1) throw Error('Expected approved article card');
  const card = cards.children[0];
  const cardIds = codes(card);
  card.events.click();
  const reader = elements.get('#article-reader');
  process.stdout.write(JSON.stringify({cardIds, readerIds: codes(reader),
    cardText: card.textContent, readerText: reader.textContent,
    mutated: before !== JSON.stringify(article)}));
});
'''


class ArticleIdentityTests(unittest.TestCase):
    def setUp(self):
        self.article = json.loads((ROOT / 'dist/articles.json').read_text())['articles'][0]

    def test_static_reference_preserves_the_approved_version(self):
        original = copy.deepcopy(self.article)
        rendered = build_pages.article_html(self.article)
        self.assertIn('Référence de l’article : ', rendered)
        self.assertIn(f'<code>{self.article["article_id"]}</code>', rendered)
        self.assertEqual(self.article, original)
        self.assertEqual(build_pages.content_sha256(self.article['draft']), self.article['draft_sha256'])
        self.assertEqual(self.article['human_decision']['draft_sha256'], self.article['draft_sha256'])

    def test_static_reference_escapes_markup(self):
        self.article['article_id'] = 'article-<script>alert("x")</script>&'
        rendered = build_pages.article_html(self.article)
        self.assertIn('<code>article-&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;&amp;</code>', rendered)
        self.assertNotIn('<script>', rendered)

    def browser_reference(self, article):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required to verify the Journal renderer')
        result = subprocess.run([node, '-e', NODE_RENDER, str(ROOT / 'dist/app.js')],
                                input=json.dumps(article), text=True, capture_output=True,
                                check=True, timeout=10)
        return json.loads(result.stdout)

    def test_journal_and_reader_show_the_same_stable_reference(self):
        result = self.browser_reference(self.article)
        article_id = self.article['article_id']
        self.assertEqual(result['cardIds'], [article_id])
        self.assertIn(article_id, result['readerIds'])
        self.assertIn('Référence de l’article : ' + article_id, result['cardText'])
        self.assertIn('Référence de l’article : ' + article_id, result['readerText'])
        self.assertFalse(result['mutated'])

    def test_journal_treats_reference_as_text(self):
        self.article['article_id'] = 'article-<img src=x onerror=alert(1)>&'
        result = self.browser_reference(self.article)
        self.assertEqual(result['cardIds'], [self.article['article_id']])
        self.assertIn(self.article['article_id'], result['readerIds'])
        self.assertFalse(result['mutated'])


if __name__ == '__main__':
    unittest.main()
