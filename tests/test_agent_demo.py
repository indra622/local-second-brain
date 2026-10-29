"""Exercise the checkout example through its public subprocess interface."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from local_knowledge_wiki.storage import LOCK_MARKER, Store


PROJECT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT / 'examples/reuse-inputs'


class AgentDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'output with spaces'

    def demo(self, code=0):
        result = subprocess.run([sys.executable, str(PROJECT / 'examples/knowledge_reuse.py'),
                                 '--output', str(self.output)], cwd=PROJECT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def load(self, name):
        return json.loads((self.output / name).read_text())

    def test_full_demo_recalls_reuses_and_preserves_previous_bytes(self):
        summary = json.loads(self.demo().stdout)
        self.assertEqual(summary['initial_hits'], 0)
        self.assertEqual(summary['revisions'], 3)
        self.assertEqual(summary['preserved_files'], 5)
        self.assertEqual(summary['trust'], 'unverified')
        self.assertEqual(summary['check'], {'invalid': [], 'warnings': [], 'stale': [], 'concepts': 3})
        self.assertEqual(summary, self.load('summary.json'))
        before, after = self.load('reuse-before.json'), self.load('reuse-after.json')
        self.assertEqual(before['body'], (FIXTURES / 'body-v1.md').read_text())
        self.assertEqual(after['body'], (FIXTURES / 'body-v2.md').read_text())
        self.assertEqual(before['reused_revision'], 'concepts/lantern/r000002.md')
        self.assertEqual(after['reused_revision'], 'concepts/lantern/r000003.md')
        self.assertEqual((before['trust'], after['trust']), ('machine-confirmed', 'unverified'))
        events = self.load('transcript.json')
        search = [e['result'] for e in events if e['arguments'][0] == 'search']
        self.assertEqual(search[0], [])
        self.assertEqual([[n['path'] for n in hits] for hits in search[1:]],
                         [[before['reused_revision']], [after['reused_revision']]])
        history = next(e['result'] for e in events if e['arguments'][0] == 'history')
        self.assertEqual([n['current'] for n in history], [False, False, True])
        self.assertEqual([n['trust'] for n in history], ['unverified', 'machine-confirmed', 'unverified'])
        bundle = self.output / 'wiki'
        review = next(e['result'] for e in events if e['arguments'][0] == 'review')['verified'][0]
        self.assertEqual(review['by'], 'process:synthetic-demo')
        original = bundle / 'concepts/lantern/r000001.md'
        self.assertEqual(review['x-second-brain-target']['sha256'], hashlib.sha256(original.read_bytes()).hexdigest())
        for version in ('v1', 'v2'):
            source = bundle / f'sources/lantern-{version}/content.raw'
            self.assertEqual(source.read_bytes(), (FIXTURES / f'source-{version}.txt').read_bytes())
        shown = [e['result'] for e in events if e['arguments'][0] == 'show']
        for note in shown:
            # Saved outputs must still describe the immutable revision bytes on disk.
            raw = (bundle / note['path']).read_bytes()
            self.assertTrue(raw.endswith(note['body'].encode('utf-8')))
        self.assertNotIn('verified', shown[-1]['metadata'])
        comparison = next(e['result']['diff'] for e in events if e['arguments'][0] == 'diff')
        self.assertIn('-Use amber trays and two bells', comparison)
        self.assertIn('+Use cobalt trays and three bells', comparison)
        with Store(bundle) as store, store.lock():
            self.assertEqual((bundle / '.lkw.lock').read_bytes(), LOCK_MARKER)

    def test_existing_empty_output_works(self):
        self.output.mkdir()
        self.demo()
        self.assertEqual(self.load('summary.json')['revisions'], 3)

    def test_nonempty_output_is_refused_without_changes(self):
        self.output.mkdir()
        sentinel = self.output / 'keep.raw'
        sentinel.write_bytes(b'private sentinel\x00\xff\r\n')
        self.assertIn('new or empty', self.demo(code=2).stderr)
        self.assertEqual(list(self.output.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_bytes(), b'private sentinel\x00\xff\r\n')

    def test_rerun_is_refused_and_completed_output_unchanged(self):
        self.demo()
        before = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        self.demo(code=2)
        self.assertEqual(before, {p.relative_to(self.output): p.read_bytes()
                                  for p in self.output.rglob('*') if p.is_file()})

    def test_file_and_symlink_outputs_are_refused(self):
        self.output.write_bytes(b'keep')
        self.demo(code=2)
        self.assertEqual(self.output.read_bytes(), b'keep')
        self.output.unlink()
        target = Path(self.temp.name) / 'empty'
        target.mkdir()
        self.output.symlink_to(target, target_is_directory=True)
        self.demo(code=2)
        self.assertTrue(self.output.is_symlink())
        self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
