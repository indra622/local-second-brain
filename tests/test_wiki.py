import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from local_knowledge_wiki.format import context, parse, timestamp, validate
from local_knowledge_wiki.storage import Store, WikiError


class MetadataTests(unittest.TestCase):
    def test_minimal_unknown_and_absent_status(self):
        meta, _ = parse('---\ntype: New custom type\nfuture: {nested: [1, 2], 7: extension}\n---\ntext')
        self.assertEqual(validate(meta), [])
        ctx = context(meta, timestamp('2026-01-01T00:00:00Z'), [])
        self.assertEqual((ctx['status'], ctx['trust'], ctx['stale']), ('stable', 'unverified', None))

    def test_invalid_yaml_and_duplicate(self):
        for text in ('---\ntype: [\n---\n', '---\ntype: One\ntype: Two\n---\n',
                     '---\n[type]\n---\n', '---\ntype: One\n', '# No metadata'):
            with self.subTest(text=text), self.assertRaises(WikiError):
                parse(text)

    def test_offset_and_stale_boundary(self):
        instant = timestamp('2026-01-01T09:00:00+09:00')
        meta = {'type': 'Note', 'stale_after': '2026-01-01T00:00:00Z'}
        self.assertFalse(context(meta, instant - timedelta(microseconds=1), [])['stale'])
        self.assertTrue(context(meta, instant, [])['stale'])
        self.assertTrue(context(meta, instant + timedelta(microseconds=1), [])['stale'])
        for date in ('2026-01-01T00:00:00', '2026-01-01', '2026-99-01T00:00:00Z'):
            with self.subTest(date=date), self.assertRaises(WikiError):
                timestamp(date)

    def test_verified_mapping_list_and_generated_without_at(self):
        now = timestamp('2026-01-01T00:00:00Z')
        for event, trust in (({'by': 'human:synthetic', 'at': now}, 'human-reviewed'),
                             ([{'by': 'process:synthetic', 'at': now}], 'machine-confirmed')):
            meta = {'type': 'Note', 'verified': event, 'generated': {'by': 'test/1'}}
            self.assertEqual(validate(meta), [])
            self.assertEqual(context(meta, now, [])['trust'], trust)

    def test_invalid_optional_metadata(self):
        for fields in ({'sources': [{}]}, {'sources': [{'resource': '  '}]},
                       {'generated': {}}, {'generated': {'by': 'test/1', 'at': '2026-01-01T00:00:00'}},
                       {'verified': {'by': 'human:synthetic'}}, {'verified': 'yes'},
                       {'verified': [{'at': '2026-01-01T00:00:00Z'}]},
                       {'status': 'unknown'}, {'tags': 'one'}, {'type': ''},
                       {'sources': [{'resource': 'scope', 'last_modified': '2026-01-01'}]},
                       {'usage_window': {'from': '2026-01-01T00:00:00'}}):
            with self.subTest(fields=fields):
                self.assertTrue(validate({'type': 'Note', **fields}))
        self.assertEqual(validate({'type': 'Note', 'sources': [{'resource': 'synthetic population'}]}), [])


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bundle = self.base / 'bundle'
        self.source = self.base / 'input.txt'
        self.source.write_bytes(b'\xef\xbb\xbfsynthetic garden\r\n\xff\x00')
        self.body = self.base / 'body.md'
        self.body.write_text('# Synthetic garden\n\nwater garden\n', encoding='utf-8')
        self.run_cli('init', self.bundle)

    def run_cli(self, *args, code=0):
        result = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', *map(str, args)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def capture(self, source_id='note'):
        return self.run_cli('capture', self.bundle, self.source, '--id', source_id,
                            '--actor', 'human:synthetic', '--resource', 'synthetic:note')

    def curate(self, **kwargs):
        return self.run_cli('curate', self.bundle, 'garden', '--body', self.body,
                            '--source', 'note', '--actor', 'test-agent/1', **kwargs)

    def test_pristine_workflow_and_revision_preservation(self):
        self.capture()
        raw = self.bundle / 'sources/note/content.raw'
        self.assertEqual(raw.read_bytes(), self.source.read_bytes())
        provenance = json.loads(raw.with_name('provenance.json').read_text())
        self.assertEqual(provenance['sha256'], hashlib.sha256(raw.read_bytes()).hexdigest())
        first = self.curate()['revision']
        original = (self.bundle / first).read_bytes()
        index = self.bundle / 'index.md'
        index.write_text(index.read_text() + '\nHuman notes stay here.\n')
        self.body.write_text('# Garden\nwater twice\n')
        second = self.curate()['revision']
        self.assertNotEqual(first, second)
        self.assertEqual((self.bundle / first).read_bytes(), original)
        self.assertIn('Human notes stay here.', index.read_text())
        self.assertIn(second, index.read_text())
        self.assertNotIn(first, index.read_text())
        meta, _ = parse((self.bundle / second).read_text())
        self.assertNotIn('verified', meta)
        results = self.run_cli('search', self.bundle, 'garden')
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(r['current'] for r in results), 1)
        self.assertEqual(results, self.run_cli('search', self.bundle, 'garden'))
        self.assertEqual(results[0]['trust'], 'unverified')
        self.assertEqual(results[0]['status'], 'draft')
        self.assertEqual(self.run_cli('check', self.bundle)['invalid'], [])

    def test_init_and_source_are_non_destructive(self):
        before = (self.bundle / 'index.md').read_bytes()
        self.run_cli('init', self.bundle, code=2)
        self.assertEqual((self.bundle / 'index.md').read_bytes(), before)
        self.capture()
        self.source.write_bytes(b'changed')
        self.run_cli('capture', self.bundle, self.source, '--id', 'note', '--actor', 'x/1',
                     '--resource', 'synthetic', code=2)
        self.assertNotEqual((self.bundle / 'sources/note/content.raw').read_bytes(), b'changed')
        nonempty = self.base / 'nonempty'
        nonempty.mkdir()
        (nonempty / 'keep').write_text('human')
        self.run_cli('init', nonempty, code=2)
        self.assertEqual(sorted(p.name for p in nonempty.iterdir()), ['keep'])

    def test_unsafe_ids_and_symlinks(self):
        for value in ('../escape', '/escape', 'a/b', '..', 'UPPER', 'x' * 65):
            self.run_cli('capture', self.bundle, self.source, '--id', value,
                         '--actor', 'x/1', '--resource', 'synthetic', code=2)
        outside = self.base / 'outside'
        outside.mkdir()
        (self.bundle / 'sources').symlink_to(outside, target_is_directory=True)
        self.run_cli('capture', self.bundle, self.source, '--id', 'escape',
                     '--actor', 'x/1', '--resource', 'synthetic', code=2)
        self.assertEqual(list(outside.iterdir()), [])
        self.run_cli('check', self.bundle, code=2)
        with Store(self.bundle) as store, self.assertRaises(WikiError):
            store.read('../input.txt')
        alias = self.base / 'alias'
        alias.symlink_to(self.bundle, target_is_directory=True)
        self.run_cli('init', alias, code=2)

    def test_input_and_revision_symlink_escape(self):
        self.capture()
        self.body.unlink()
        self.body.symlink_to(self.source)
        self.curate(code=2)
        self.body.unlink()
        self.body.write_text('garden')
        outside = self.base / 'outside'
        outside.mkdir()
        (self.bundle / 'concepts').symlink_to(outside, target_is_directory=True)
        self.curate(code=2)
        self.assertEqual(list(outside.iterdir()), [])

    def test_lock_and_edited_index_block(self):
        self.capture()
        (self.bundle / '.lkw.lock').write_text('other writer')
        self.curate(code=2)
        self.assertEqual((self.bundle / '.lkw.lock').read_text(), 'other writer')
        (self.bundle / '.lkw.lock').unlink()
        index = self.bundle / 'index.md'
        index.write_text(index.read_text().replace('<!-- lkw:current:end -->',
                                                 'Human addition\n<!-- lkw:current:end -->'))
        self.curate(code=2)
        self.assertFalse((self.bundle / 'concepts').exists())

    def test_metadata_link_and_freshness_categories(self):
        (self.bundle / 'note.md').write_text(
            '---\ntype: Note\nstale_after: 2026-01-01T00:00:00Z\n---\n'
            '[missing](gone.md)\n[escape](../outside)\n'
            '```\n[code](not-a-link.md)\n```\n')
        report = self.run_cli('check', self.bundle, '--now', '2026-01-01T00:00:00Z')
        self.assertEqual(report['invalid'], [])
        self.assertEqual(len(report['warnings']), 2)
        self.assertEqual(report['stale'], ['note.md'])
        (self.bundle / 'bad.md').write_text('---\ntype: [\n---\n')
        report = self.run_cli('check', self.bundle, code=1)
        self.assertEqual(report['invalid'][0]['path'], 'bad.md')
        (self.bundle / 'bad.md').write_text('---\ntype: Note\ngenerated: {by: x/1, at: 2026-01-01T00:00:00}\n---\n')
        self.assertTrue(self.run_cli('check', self.bundle, code=1)['invalid'])

    def test_reserved_files(self):
        (self.bundle / 'log.md').write_text('# History\n\n## 2026-01-01\nSynthetic entry\n')
        directory = self.bundle / 'nested'
        directory.mkdir()
        (directory / 'index.md').write_text('# Directory\n')
        report = self.run_cli('check', self.bundle)
        self.assertEqual(report['concepts'], 0)
        (directory / 'index.md').write_text('---\ntype: Note\n---\n')
        self.assertTrue(self.run_cli('check', self.bundle, code=1)['invalid'])

    def test_missing_source_and_body_frontmatter(self):
        self.curate(code=2)
        self.capture()
        self.body.write_text('---\ntype: Note\n---\nbody')
        self.curate(code=2)
        self.assertFalse((self.bundle / 'concepts').exists())

    def test_search_surfaces_stale_and_invalid_context(self):
        (self.bundle / 'note.md').write_text(
            '---\ntype: Note\nstale_after: 2026-01-01T00:00:00Z\n'
            'verified: {by: human:synthetic, at: 2025-12-01T00:00:00Z}\n---\ngarden')
        result = self.run_cli('search', self.bundle, 'garden', '--now', '2026-01-01T00:00:00Z')[0]
        self.assertEqual((result['status'], result['trust'], result['stale']),
                         ('stable', 'human-reviewed', True))
        (self.bundle / 'note.md').write_text('---\ntype: Note\nverified: broken\n---\ngarden')
        result = self.run_cli('search', self.bundle, 'garden')[0]
        self.assertEqual(result['trust'], 'invalid-metadata')
        self.assertTrue(result['metadata_errors'])

    def test_source_link_warning_and_unknown_root_version(self):
        (self.bundle / 'note.md').write_text(
            '---\ntype: Note\nsources: [{resource: ./missing.raw}]\n---\ngarden')
        report = self.run_cli('check', self.bundle)
        self.assertEqual(len(report['warnings']), 1)
        self.assertEqual(report['invalid'], [])
        index = self.bundle / 'index.md'
        index.write_text(index.read_text().replace("'0.2'", "'99.0'"))
        self.assertEqual(len(self.run_cli('check', self.bundle)['warnings']), 2)

    def test_concurrent_curate_preserves_all_successful_revisions(self):
        self.capture()
        command = [sys.executable, '-m', 'local_knowledge_wiki.cli', 'curate', str(self.bundle),
                   'garden', '--body', str(self.body), '--source', 'note', '--actor', 'test/1']
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        for process in processes:
            process.communicate(timeout=10)
        successful = sum(p.returncode == 0 for p in processes)
        self.assertGreaterEqual(successful, 1)
        self.assertTrue(all(p.returncode in (0, 2) for p in processes))
        revisions = sorted((self.bundle / 'concepts/garden').glob('r*.md'))
        self.assertEqual(len(revisions), successful)
        self.assertIn(revisions[-1].name, (self.bundle / 'index.md').read_text())
        self.assertEqual(self.run_cli('check', self.bundle)['invalid'], [])

    def test_concurrent_capture_has_one_winner(self):
        command = [sys.executable, '-m', 'local_knowledge_wiki.cli', 'capture', str(self.bundle),
                   str(self.source), '--id', 'note', '--actor', 'test/1', '--resource', 'synthetic']
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        for process in processes:
            process.communicate(timeout=10)
        self.assertEqual(sorted(p.returncode for p in processes), [0, 2])
        self.assertEqual((self.bundle / 'sources/note/content.raw').read_bytes(), self.source.read_bytes())


if __name__ == '__main__':
    unittest.main()
