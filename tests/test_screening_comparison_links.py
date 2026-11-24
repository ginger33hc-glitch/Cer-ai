"""Dependency-free regression checks for public comparison links.

Run: python -m unittest discover -s tests -p test_screening_comparison_links.py -v
"""
import ast
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ('en', 'keratoconus-screening-public.html', '/corneal-ectasia-screening-systems',
     'corneal-ectasia-screening-systems.html', 'comparison-table', 'screening-systems'),
    ('tr', 'tr-keratokonus-tarama.html', '/tr/korneal-ektazi-tarama-sistemleri',
     'tr-korneal-ektazi-tarama-sistemleri.html', 'karsilastirma-tablosu', 'tarama-sistemleri'),
)

class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

class ComparisonLinks(unittest.TestCase):
    def test_links_resolve_to_same_language_table(self):
        for lang, source, route, target, fragment, section in CASES:
            with self.subTest(language=lang):
                doc = Document((ROOT / 'static' / source).read_text())
                dest = Document((ROOT / 'static' / target).read_text())
                links = [a for tag, a in doc.elements if tag == 'a'
                         and a.get('href') == route + '#' + fragment]
                self.assertEqual(len(links), 1)
                self.assertNotIn('nofollow', links[0].get('rel', '').split())
                self.assertEqual([a['lang'] for tag, a in dest.elements if tag == 'html'], [lang])
                self.assertEqual([(tag, a['id']) for tag, a in dest.elements
                                  if a.get('id') == fragment], [('table', fragment)])
                self.assertTrue(any(tag == 'a' and a.get('href') == '#' + section
                                    for tag, a in doc.elements))
                for document in (doc, dest):
                    ids = [a['id'] for _, a in document.elements if 'id' in a]
                    self.assertEqual(len(ids), len(set(ids)))
                for tag, a in doc.elements:
                    href = a.get('href', '')
                    if tag == 'a' and href.startswith('#'):
                        self.assertTrue(any(b.get('id') == urlsplit(href).fragment
                                            for _, b in doc.elements), href)

    def test_destination_routes_are_registered(self):
        tree = ast.parse((ROOT / 'public_site.py').read_text())
        routes = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == 'get' and dec.args and isinstance(dec.args[0], ast.Constant):
                        routes[dec.args[0].value] = ast.unparse(node)
        for _, _, route, target, _, _ in CASES:
            with self.subTest(route=route):
                self.assertIn(route, routes)
        # Both registered handlers use the corresponding static file constants.
        text = (ROOT / 'public_site.py').read_text()
        self.assertIn('static/corneal-ectasia-screening-systems.html', text)
        self.assertIn('static/tr-korneal-ektazi-tarama-sistemleri.html', text)

if __name__ == '__main__':
    unittest.main()
