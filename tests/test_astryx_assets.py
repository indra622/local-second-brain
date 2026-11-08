"""Shipped assets remain reproducible without Node at Python runtime."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'frontend/astryx'
DIST = ROOT / 'src/local_knowledge_wiki/web/astryx'


class AstryxAssetsTests(unittest.TestCase):
    def test_source_lock_shared_projection_and_distribution_match_manifest(self):
        manifest = json.loads((DIST / 'build-manifest.json').read_text())
        self.assertEqual(set(p.name for p in DIST.iterdir()),
                         {'index.html', 'app.js', 'app.css', 'notices.txt', 'build-manifest.json'})
        for name, expected in manifest['source'].items():
            if name == 'src/shared-map.mjs':
                data = (ROOT / 'src/local_knowledge_wiki/web/map.js').read_bytes() + b'\nexport {KnowledgeMap};\n'
            else:
                data = (SOURCE / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected, name)
        for name, info in manifest['assets'].items():
            data = (DIST / name).read_bytes()
            self.assertEqual(len(data), info['bytes'], name)
            self.assertEqual(hashlib.sha256(data).hexdigest(), info['sha256'], name)
        package = json.loads((SOURCE / 'package.json').read_text())
        lock = json.loads((SOURCE / 'package-lock.json').read_text())
        for name, version in package['dependencies'].items():
            self.assertNotIn('^', version)
            self.assertEqual(lock['packages']['node_modules/' + name]['version'], version)
        self.assertEqual(manifest['packages']['@astryxdesign/core'], '0.7.11')
        self.assertTrue(manifest['packages']['react'].startswith('19.'))

    def test_notice_covers_actual_packages_and_html_has_only_local_entrypoints(self):
        notices = (DIST / 'notices.txt').read_text()
        manifest = json.loads((DIST / 'build-manifest.json').read_text())
        for name, version in manifest['packages'].items():
            self.assertIn(name + '@' + version, notices)
        html = (DIST / 'index.html').read_text()
        self.assertIn('./app.js', html)
        self.assertIn('./app.css', html)
        self.assertNotIn('<iframe', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('https://', html)
