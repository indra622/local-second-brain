"""Product export regressions; no model, private data or dependency installation."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import export_knowledge_kit as kit


class PacketTests(unittest.TestCase):
    def test_product_only_and_manifest_bytes(self):
        with tempfile.TemporaryDirectory(prefix='knowledge-packet-') as directory:
            output = Path(directory) / 'packet'
            result = kit.export(output)
            names = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
            self.assertIn('knowledge-kit/START.md', names)
            self.assertIn('workflows/AGENT-WORKFLOW.md', names)
            self.assertIn('docs/reference.ko.md', names)
            self.assertFalse(any(n.startswith(('examples/', 'tests/', 'src/', 'scripts/')) for n in names))
            self.assertFalse(any('rubric' in n or 'requests.json' in n for n in names))
            for row in result['files']:
                self.assertEqual(hashlib.sha256((output / row['path']).read_bytes()).hexdigest(), row['export_sha256'])
            profile = json.loads((output / 'knowledge-kit/profile.example.json').read_text())
            self.assertFalse(profile['access']['write_bundle'])
            self.assertFalse(profile['save']['triggers']['enabled'])
            self.assertEqual(profile['provider']['text_transfer'], 'not_authorized')

    def test_existing_and_symlink_output_preserved(self):
        with tempfile.TemporaryDirectory(prefix='knowledge-existing-') as directory:
            root = Path(directory); output = root / 'existing'; output.mkdir()
            sentinel = output / 'user-file'; sentinel.write_bytes(b'preserve')
            alias = root / 'alias'; alias.symlink_to(output, target_is_directory=True)
            for target in (output, alias):
                with self.assertRaises(ValueError): kit.export(target)
                self.assertEqual(sentinel.read_bytes(), b'preserve')
                self.assertEqual(list(output.iterdir()), [sentinel])
            with self.assertRaises(ValueError): kit.export(kit.ROOT / 'forbidden-packet')

    def test_source_symlink_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory(prefix='knowledge-source-') as directory:
            root = Path(directory); source = root / 'source'; source.mkdir()
            external = root / 'external'; external.write_bytes(b'unrelated synthetic fixture')
            (source / 'entry.md').symlink_to(external)
            output = root / 'packet'
            with patch.object(kit, 'ROOT', source), patch.object(kit, 'PRODUCT', ('entry.md',)), patch.object(kit, 'REFERENCES', ()):
                with self.assertRaises(ValueError): kit.export(output)
            self.assertFalse(output.exists())
            self.assertEqual(external.read_bytes(), b'unrelated synthetic fixture')


if __name__ == '__main__':
    unittest.main()
