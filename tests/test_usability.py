"""Synthetic end-to-end tests of read-only CLI behavior."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class UsabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'wiki'
        self.cli('init', self.bundle)
        self.source = self.root / 'source'
        self.source.write_text('synthetic')
        self.cli('capture', self.bundle, self.source, '--id', 'source', '--actor', 'test/1',
                 '--resource', 'synthetic')
        self.body = self.root / 'body'
        self.body.write_text('달빛 garden old\n')
        self.curate('--status', 'deprecated', '--stale-after', '2020-01-01T00:00:00Z')
        self.body.write_text('달빛 garden new\n')
        self.curate('--status', 'stable', '--stale-after', '2099-01-01T00:00:00Z')

    def cli(self, *args, code=0, text=False):
        result = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', *map(str, args)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        if code == 2:
            return result.stderr
        return result.stdout if text else json.loads(result.stdout)

    def curate(self, *args):
        return self.cli('curate', self.bundle, 'garden', '--body', self.body,
                        '--source', 'source', '--actor', 'test/1', '--title', '달빛 Garden', *args)

    def search(self, *args):
        return self.cli('search', self.bundle, 'garden', '--now', '2026-01-01T00:00:00Z', *args)

    def test_browse_preserves_every_byte_and_marks_current(self):
        before = {p.relative_to(self.bundle): p.read_bytes() for p in self.bundle.rglob('*') if p.is_file()}
        notes = self.cli('list', self.bundle)
        history = self.cli('history', self.bundle, 'garden')
        self.assertEqual(notes, history)
        self.assertEqual([n['current'] for n in notes], [False, True])
        self.assertEqual([n['path'] for n in notes], ['concepts/garden/r000001.md', 'concepts/garden/r000002.md'])
        current = self.cli('show', self.bundle, 'garden')
        self.assertEqual(current['body'], '달빛 garden new\n')
        old = self.cli('show', self.bundle, 'garden', '--revision', 'r000001')
        self.assertEqual((old['status'], old['trust'], old['stale']), ('deprecated', 'unverified', True))
        diff = self.cli('diff', self.bundle, 'garden', 'r000001', 'r000002')['diff']
        self.assertIn('--- concepts/garden/r000001.md\n+++ concepts/garden/r000002.md', diff)
        self.assertIn('-달빛 garden old\n+달빛 garden new\n', diff)
        self.assertIn('-status: deprecated', diff)
        self.assertEqual(self.cli('diff', self.bundle, 'garden', 'r000002', 'r000002')['diff'], '')
        after = {p.relative_to(self.bundle): p.read_bytes() for p in self.bundle.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_human_modes_and_empty_results(self):
        for command, args in [('list', []), ('history', ['garden']), ('show', ['garden']),
                              ('diff', ['garden', 'r000001', 'r000002']), ('search', ['garden'])]:
            output = self.cli(command, self.bundle, *args, '--format', 'text', text=True)
            self.assertIn('달빛', output)
            if command != 'diff':
                self.assertIn('current', output)
                self.assertIn('trust:', output)
        self.assertIn('No results.', self.cli('search', self.bundle, 'missing', '--format', 'text', text=True))

    def test_default_search_compatibility_and_filters(self):
        hits = self.search()
        self.assertEqual(len(hits), 2)
        self.assertEqual([h['score'] for h in hits], [2, 2])
        self.assertEqual([h['current'] for h in hits], [False, True])
        for key in ('path', 'score', 'current', 'status', 'trust', 'stale', 'stale_after',
                    'generated', 'verified', 'metadata_errors'):
            self.assertIn(key, hits[0])
        self.assertEqual(self.search(), hits)
        self.assertEqual(self.search('--current-only'), [hits[1]])
        self.assertEqual(self.search('--status', 'deprecated', '--freshness', 'stale'), [hits[0]])
        self.assertEqual(self.search('--current-only', '--freshness', 'fresh', '--status', 'stable'), [hits[1]])
        self.assertEqual(self.search('--current-only', '--status', 'deprecated'), [])
        self.assertEqual(self.cli('search', self.bundle, 'gard'), [])

    def test_snippet_collapses_whitespace_and_limits_unicode(self):
        self.body.write_text('garden\n\n달빛\t' + '가' * 200)
        self.curate()
        hit = self.search('--current-only')[0]
        self.assertEqual(hit['snippet'], ('garden 달빛 ' + '가' * 200)[:159] + '…')
        self.assertEqual(len(hit['snippet']), 160)

    def test_imported_notes_unknown_current_and_freshness(self):
        (self.bundle / 'index.md').write_text('# Imported OKF\n')
        (self.bundle / 'import.md').write_text('---\ntype: Concept\n---\ngarden')
        self.assertTrue(all(h['current'] is None for h in self.search()))
        self.assertEqual(self.search('--current-only'), [])
        unknown = self.search('--freshness', 'unknown')
        self.assertEqual([h['path'] for h in unknown], ['import.md'])
        self.assertEqual(len(self.search('--freshness', 'fresh')), 1)
        self.assertIn('No indexed current', self.cli('show', self.bundle, 'garden', code=2))
        self.assertEqual(self.cli('show', self.bundle, 'garden', '--revision', 'r000001')['current'], None)

    def test_malformed_metadata_has_deliberate_context_and_errors(self):
        path = self.bundle / 'concepts/garden/r000002.md'
        for content in ('---\ntype: [\n---\ngarden',
                        '---\ntype: Concept\nstatus: [bad]\nverified: broken\nstale_after: nope\n---\ngarden'):
            path.write_text(content)
            note = self.cli('show', self.bundle, 'garden')
            self.assertEqual(note['trust'], 'invalid-metadata')
            self.assertTrue(note['metadata_errors'])
            self.assertTrue(self.cli('history', self.bundle, 'garden')[1]['metadata_errors'])
            self.assertIn('Metadata error:', self.cli('show', self.bundle, 'garden', '--format', 'text', text=True))
            self.assertEqual(self.search('--current-only', '--freshness', 'fresh'), [])
            self.assertEqual(self.search('--current-only', '--status', 'stable'), [])
            self.assertEqual(len(self.search('--current-only', '--freshness', 'unknown')), 1)
            self.assertIn('Cannot diff', self.cli('diff', self.bundle, 'garden', 'r000001', 'r000002', code=2))
        path.write_bytes(b'\xff')
        self.assertIn('UTF-8', self.cli('show', self.bundle, 'garden')['metadata_errors'][0])
        self.assertTrue(self.cli('check', self.bundle, code=1)['invalid'])
        path.write_text('---\ntype: Concept\n2026-01-01: extension\n---\ngarden')
        for mode in ('json', 'text'):
            self.assertNotIn('Traceback', self.cli('show', self.bundle, 'garden', '--format', mode, code=2))

    def test_freshness_uses_only_deadline_even_with_unrelated_errors(self):
        path = self.bundle / 'concepts/garden/r000002.md'
        for deadline, expected, label in [('2099-01-01T00:00:00Z', False, 'fresh'),
                                          ('2020-01-01T00:00:00Z', True, 'stale'),
                                          ('2099-01-01T00:00:00', None, 'unknown'),
                                          ('invalid', None, 'unknown')]:
            path.write_text('---\ntype: Concept\nverified: broken\nstale_after: '
                            + deadline + '\n---\ngarden')
            note = self.cli('show', self.bundle, 'garden', '--now', '2026-01-01T00:00:00Z')
            self.assertIs(note['stale'], expected)
            self.assertEqual(note['trust'], 'invalid-metadata')
            self.assertEqual(len(self.search('--current-only', '--freshness', label)), 1)
            output = self.cli('show', self.bundle, 'garden', '--format', 'text', text=True)
            self.assertIn('freshness unknown' if expected is None else '| ' + label, output)
            for other in {'fresh', 'stale', 'unknown'} - {label}:
                self.assertEqual(self.search('--current-only', '--freshness', other), [])

    def test_missing_and_unsafe_arguments_are_errors(self):
        for command, args in [('show', ['missing']), ('history', ['missing']),
                              ('show', ['../escape']), ('history', ['/escape']),
                              ('show', ['garden', '--revision', '../r000001']),
                              ('show', ['garden', '--revision', 'r000000']),
                              ('diff', ['garden', 'r000001', 'r999999'])]:
            error = self.cli(command, self.bundle, *args, code=2)
            self.assertIn('error', json.loads(error))
        self.assertIn('second-brain:', self.cli('show', self.bundle, 'missing', '--format', 'text', code=2))

    def test_application_directories_and_symlinks_are_ignored(self):
        for parent in (self.bundle, self.bundle / 'concepts/garden'):
            (parent / '.obsidian').mkdir()
            (parent / '.obsidian/bad.md').write_text('malformed garden')
            (parent / '.obsidian/escape').symlink_to(self.root)
            (parent / '.git').symlink_to(self.root, target_is_directory=True)
        (self.bundle / 'nested').mkdir()
        (self.bundle / 'nested/.git').mkdir()
        (self.bundle / 'nested/.git/bad.md').write_text('malformed garden')
        (self.bundle / 'nested/.obsidian').symlink_to(self.root)
        self.assertEqual(len(self.search()), 2)
        self.assertEqual(self.cli('check', self.bundle)['invalid'], [])
        self.assertEqual(len(self.cli('list', self.bundle)), 2)
        self.assertEqual(len(self.cli('history', self.bundle, 'garden')), 2)
        self.curate()
        self.assertEqual(len(self.cli('history', self.bundle, 'garden')), 3)
        self.assertEqual((self.bundle / '.obsidian/bad.md').read_text(), 'malformed garden')
        self.assertTrue((self.bundle / '.git').is_symlink())

    def test_hidden_knowledge_is_scanned_and_regular_symlinks_rejected(self):
        hidden = self.bundle / '.knowledge'
        hidden.mkdir()
        (hidden / 'note.md').write_text('---\ntype: Concept\n---\ngarden')
        self.assertIn('.knowledge/note.md', [h['path'] for h in self.search()])
        (hidden / 'bad.md').write_text('garden')
        self.assertTrue(self.cli('check', self.bundle, code=1)['invalid'])
        (hidden / 'link.md').symlink_to(self.source)
        for command, args in [('search', ['garden']), ('check', []), ('list', []),
                              ('history', ['garden']), ('show', ['garden'])]:
            self.assertIn('Symlinks', self.cli(command, self.bundle, *args, code=2))

    def test_diff_explains_missing_final_newline(self):
        self.body.write_text('달빛 garden last line')
        self.curate()
        diff = self.cli('diff', self.bundle, 'garden', 'r000002', 'r000003')['diff']
        self.assertIn('+달빛 garden last line\n\\ No newline at end of file\n', diff)

    def test_direct_revision_symlink_is_never_read(self):
        path = self.bundle / 'concepts/garden/r000002.md'
        path.unlink()
        path.symlink_to(self.source)
        self.assertIn('Symlinks', self.cli('show', self.bundle, 'garden', code=2))


if __name__ == '__main__':
    unittest.main()
