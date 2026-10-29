"""Declared review events, using synthetic artifacts only."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

from local_knowledge_wiki.cli import review
from local_knowledge_wiki.format import parse, timestamp
from local_knowledge_wiki.storage import LOCK_MARKER, Store, WikiError


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'wiki'
        self.cli('init', self.bundle)
        self.input = self.root / 'source'
        self.input.write_bytes(b'synthetic evidence\r\n\xff')
        self.cli('capture', self.bundle, self.input, '--id', 'source', '--actor', 'test/1',
                 '--resource', 'synthetic')
        self.body = self.root / 'body'
        self.body.write_bytes('달빛 garden\r\nno final newline'.encode())
        self.curate()
        self.target = self.bundle / 'concepts/garden/r000001.md'
        self.evidence = 'sources/source/content.raw'

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', *map(str, args)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout) if code == 0 else result.stderr

    def curate(self):
        return self.cli('curate', self.bundle, 'garden', '--body', self.body,
                        '--source', 'source', '--actor', 'test/1')

    def record(self, revision='r000001', actor='human:synthetic', evidence=None, code=0):
        return self.cli('review', self.bundle, 'garden', '--revision', revision, '--actor', actor,
                        '--evidence', self.evidence if evidence is None else evidence, code=code)

    def snapshot(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*')
                if p.is_file() and not p.is_symlink()}

    def test_current_review_preserves_bytes_metadata_and_later_curate_is_unverified(self):
        content = self.target.read_bytes().replace(b'type: Concept', b'type: Concept\ncustom: {nested: [1, two]}')
        self.target.write_bytes(content)
        original_meta, body = parse(content.decode())
        index = self.bundle / 'index.md'
        index.write_bytes(index.read_bytes() + b'\nSynthetic index prose\n')
        low = datetime.now(timezone.utc)
        output = self.record()
        high = datetime.now(timezone.utc)
        self.assertEqual(output['revision'], 'concepts/garden/r000002.md')
        self.assertEqual(self.target.read_bytes(), content)
        current = self.cli('show', self.bundle, 'garden')
        self.assertEqual(current['body'], body)
        self.assertEqual(current['body'].encode(), self.body.read_bytes())
        self.assertEqual((current['status'], current['trust']), ('draft', 'human-reviewed'))
        meta, _ = parse((self.bundle / output['revision']).read_bytes().decode())
        self.assertEqual({k: v for k, v in meta.items() if k != 'verified'}, original_meta)
        event = output['verified'][-1]
        self.assertEqual(meta['verified'], [event])
        self.assertLessEqual(low, timestamp(event['at']))
        self.assertLessEqual(timestamp(event['at']), high)
        self.assertEqual(event['x-second-brain-target'], {
            'resource': '/concepts/garden/r000001.md', 'sha256': hashlib.sha256(content).hexdigest()})
        self.assertEqual(event['x-second-brain-evidence'], {
            'resource': '/' + self.evidence, 'sha256': hashlib.sha256(self.input.read_bytes()).hexdigest()})
        self.assertIn('Synthetic index prose', index.read_text())
        self.assertEqual(self.cli('check', self.bundle)['invalid'], [])
        self.assertEqual(self.cli('search', self.bundle, 'garden', '--current-only')[0]['trust'], 'human-reviewed')
        self.body.write_text('garden edited\n')
        self.curate()
        self.assertEqual(self.cli('show', self.bundle, 'garden')['trust'], 'unverified')
        self.assertNotIn('verified', self.cli('show', self.bundle, 'garden')['metadata'])
        self.assertEqual(self.cli('show', self.bundle, 'garden', '--revision', 'r000002')['trust'], 'human-reviewed')
        self.assertEqual(self.target.read_bytes(), content)

    def test_existing_mapping_and_list_and_date_keys_survive_round_trip(self):
        old = {'by': 'process:synthetic', 'at': '2026-01-01T00:00:00Z', date(2026, 1, 2): 'event extension'}
        for existing in (old, [old], []):
            with self.subTest(existing=existing):
                meta, body = parse(self.target.read_bytes().decode())
                meta['verified'] = existing
                meta[date(2026, 1, 1)] = {'nested': [{date(2026, 1, 3): 'retained'}]}
                meta['generated'][date(2026, 1, 4)] = 'generated extension'
                self.target.write_bytes(('---\n' + yaml.safe_dump(meta, sort_keys=False) + '---\n' + body).encode())
                output = self.record(actor='tool/1')
                if existing:
                    self.assertEqual(output['verified'][0]['2026-01-02'], 'event extension')
                stored, _ = parse((self.bundle / output['revision']).read_bytes().decode())
                self.assertEqual({k: v for k, v in stored.items() if k != 'verified'},
                                 {k: v for k, v in meta.items() if k != 'verified'})
                self.assertEqual(stored['verified'][:-1], [old] if isinstance(existing, dict) else existing)
                shown = self.cli('show', self.bundle, 'garden')
                self.assertEqual(shown['trust'], 'machine-confirmed')
                self.assertEqual(shown['metadata']['2026-01-01']['nested'][0]['2026-01-03'], 'retained')
                # Restore only the synthetic index to review each form against the same target.
                index = self.bundle / 'index.md'
                index.write_text(index.read_text().replace(output['revision'], 'concepts/garden/r000001.md'))

    def test_url_is_declared_without_network_and_machine_human_distinction(self):
        for actor in ('process:synthetic', 'tool/1', 'human:synthetic'):
            revision = self.cli('show', self.bundle, 'garden')['path'].split('/')[-1][:-3]
            result = self.record(revision=revision, actor=actor, evidence='https://example.invalid/check?q=1#part')
            self.assertEqual(result['verified'][-1]['x-second-brain-evidence'], {'resource': 'https://example.invalid/check?q=1#part'})
            self.assertEqual(self.cli('show', self.bundle, 'garden')['trust'],
                             'human-reviewed' if actor.startswith('human:') else 'machine-confirmed')
        before = self.snapshot()
        for command, args in [('check', []), ('show', ['garden']), ('search', ['garden'])]:
            self.cli(command, self.bundle, *args)
        self.assertEqual(before, self.snapshot())

    def test_invalid_evidence_and_actor_write_nothing(self):
        (self.bundle / 'empty').touch()
        for evidence in ('', ' ', 'missing', 'empty', '../source', '/../../source', 'sources/../index.md',
                         '//example.org/a', 'sources\\source', 'sources/source/', './index.md',
                         'sources/source/content.raw?x', 'sources/source/content.raw#x', '.git/a', '.obsidian/a',
                         'file:///tmp/a', 'ftp://example.org/a', 'javascript:alert(1)', 'https:relative',
                         'https:///a', 'https://', 'https://bad host/a', 'https://bad_host/a',
                         'https://user:password@example.org/a', 'https://example.org:bad/a',
                         'https://example.org:65536/a', 'https://example.org:/a', 'https://example.org/%zz',
                         'https://example.org/\na', 'https://example.org/<bad>', 'https://example.org/\x85', 'https://[invalid]/a', 'https://[::1]garbage/a'):
            with self.subTest(evidence=evidence):
                before = self.snapshot()
                self.record(evidence=evidence, code=2)
                self.assertEqual(before, self.snapshot())
        for actor in ('', ' ', 'human:', 'process:', 'agent', '/version', 'tool/', 'human:a/b',
                      'human:two words', 'tool/1/2', 'human:a\x7f', 'human:a\x80', 'tool\\name/1'):
            with self.subTest(actor=actor):
                before = self.snapshot()
                self.record(actor=actor, code=2)
                self.assertEqual(before, self.snapshot())

    def test_local_spaces_absolute_bundle_path_and_literal_percent(self):
        artifact = self.bundle / 'synthetic %20 evidence'
        artifact.write_bytes(b'non-executable synthetic artifact')
        event = self.record(evidence='/' + artifact.name)['verified'][-1]
        self.assertEqual(event['x-second-brain-evidence']['resource'], '/' + artifact.name)

    def test_invalid_metadata_and_unserializable_keys_write_nothing(self):
        for content in (b'\xff', b'no frontmatter', b'---\ntype: [\n---\n',
                        b'---\ntype: Note\nverified: broken\n---\n',
                        b'---\ntype: Note\nverified: {by: human:x}\n---\n',
                        b'---\ntype: Note\nextra: &cycle [*cycle]\n---\n',
                        b'---\ntype: Note\nextra: {1: numeric, "1": text}\n---\n'):
            with self.subTest(content=content):
                self.target.write_bytes(content)
                before = self.snapshot()
                self.record(code=2)
                self.assertEqual(before, self.snapshot())

    def test_stale_missing_invalid_revision_id_and_index_refused(self):
        self.curate()
        for revision in ('r000001', 'r999999', 'r000000', '../r000002', 'R000002', 'r2'):
            before = self.snapshot()
            self.record(revision=revision, code=2)
            self.assertEqual(before, self.snapshot())
        self.target.unlink()
        before = self.snapshot()
        self.record(revision='r000001', code=2)
        self.assertEqual(before, self.snapshot())
        for concept in ('../escape', '/escape', 'UPPER', 'missing'):
            self.cli('review', self.bundle, concept, '--revision', 'r000002', '--actor', 'human:test',
                     '--evidence', self.evidence, code=2)
        index = self.bundle / 'index.md'
        for content in ('# No managed index\n', index.read_text().replace('r000002', 'r999999')):
            index.write_text(content)
            before = self.snapshot()
            self.record(revision='r999999', code=2)
            self.assertEqual(before, self.snapshot())

    def test_direct_target_symlink_and_unrelated_traversal_are_refused(self):
        original = self.target.read_bytes()
        self.target.unlink()
        self.target.symlink_to(self.input)
        before = self.snapshot()
        self.record(code=2)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.input.read_bytes(), b'synthetic evidence\r\n\xff')
        self.target.unlink()
        self.target.write_bytes(original)
        (self.bundle / 'unrelated-link').symlink_to(self.input)
        before = self.snapshot()
        self.record(code=2)
        self.assertEqual(before, self.snapshot())

    def test_review_preserves_explicit_or_absent_status(self):
        for status in ('stable', 'deprecated', None):
            with self.subTest(status=status):
                meta, body = parse(self.target.read_bytes().decode())
                meta.pop('status', None)
                if status:
                    meta['status'] = status
                self.target.write_bytes(('---\n' + yaml.safe_dump(meta) + '---\n' + body).encode())
                result = self.record()
                new_meta, _ = parse((self.bundle / result['revision']).read_bytes().decode())
                self.assertEqual(new_meta.get('status'), status)
                index = self.bundle / 'index.md'
                index.write_text(index.read_text().replace(result['revision'], 'concepts/garden/r000001.md'))

    def test_evidence_symlinks_directories_and_fifo_refused(self):
        (self.bundle / 'escape').symlink_to(self.input)
        (self.bundle / 'directory-alias').symlink_to(self.root, target_is_directory=True)
        os.mkfifo(self.bundle / 'fifo')
        for evidence in ('escape', 'directory-alias/source', 'sources', 'fifo'):
            before = self.snapshot()
            self.record(evidence=evidence, code=2)
            self.assertEqual(before, self.snapshot())

    def test_lock_and_revision_limit_refused_and_orphan_number_preserved(self):
        lock = self.bundle / '.lkw.lock'
        lock.write_text('other writer')
        before = self.snapshot()
        self.record(code=2)
        self.assertEqual(before, self.snapshot())
        lock.write_bytes(LOCK_MARKER)
        orphan = self.target.with_name('r999999.md')
        orphan.write_bytes(self.target.read_bytes())
        before = self.snapshot()
        self.record(code=2)
        self.assertEqual(before, self.snapshot())
        orphan.rename(self.target.with_name('r000008.md'))
        self.assertTrue(self.record()['revision'].endswith('r000009.md'))

    def test_concurrent_review_has_one_winner(self):
        command = [sys.executable, '-m', 'local_knowledge_wiki.cli', 'review', str(self.bundle),
                   'garden', '--revision', 'r000001', '--actor', 'process:test', '--evidence', self.evidence]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        try:
            for process in processes:
                process.communicate(timeout=10)
            self.assertEqual(sorted(p.returncode for p in processes), [0, 2])
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        self.assertEqual(len(list(self.target.parent.glob('r*.md'))), 2)
        self.assertTrue(self.cli('show', self.bundle, 'garden')['path'].endswith('r000002.md'))

    def test_target_or_index_change_during_validation_refused_before_creation(self):
        original_read = Store.read
        for changed in ('index.md', 'concepts/garden/r000001.md'):
            with self.subTest(changed=changed):
                original = (self.bundle / changed).read_bytes()
                def read(store, path):
                    result = original_read(store, path)
                    if path == self.evidence:
                        (self.bundle / changed).write_bytes(original + b'\nconcurrent edit\n')
                    return result
                with patch.object(Store, 'read', read), self.assertRaisesRegex(WikiError, 'changed'):
                    review(self.bundle, 'garden', 'r000001', 'human:test', self.evidence)
                self.assertFalse(self.target.with_name('r000002.md').exists())
                self.assertEqual((self.bundle / '.lkw.lock').read_bytes(), LOCK_MARKER)
                with Store(self.bundle) as store, store.lock():
                    pass
                (self.bundle / changed).write_bytes(original)

    def test_index_change_after_revision_creation_is_not_overwritten(self):
        original_create = Store.create
        index = self.bundle / 'index.md'
        changed = index.read_bytes() + b'\nconcurrent index prose\n'
        def create(store, path, data):
            original_create(store, path, data)
            if path.endswith('r000002.md'):
                index.write_bytes(changed)
        with patch.object(Store, 'create', create), self.assertRaisesRegex(WikiError, 'changed'):
            review(self.bundle, 'garden', 'r000001', 'human:test', self.evidence)
        self.assertEqual(index.read_bytes(), changed)
        self.assertTrue(self.target.with_name('r000002.md').exists())
        self.assertEqual((self.bundle / '.lkw.lock').read_bytes(), LOCK_MARKER)
        with Store(self.bundle) as store, store.lock():
            pass

    def test_required_options_fail_without_effects(self):
        for options in ([], ['--revision', 'r000001'],
                        ['--revision', 'r000001', '--actor', 'human:test']):
            before = self.snapshot()
            self.cli('review', self.bundle, 'garden', *options, code=2)
            self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
