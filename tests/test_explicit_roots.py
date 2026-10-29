"""Explicit directory aliases remain distinct from forbidden internal/file links."""

import errno
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_knowledge_wiki.storage import LOCK_MARKER, Store, WikiError, capture, init, read_input


class ExplicitRootTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'wiki'
        init(self.bundle)
        self.alias = self.root / 'wiki-alias'
        self.alias.symlink_to(self.bundle, target_is_directory=True)
        self.inputs = self.root / 'inputs'
        self.inputs.mkdir()
        self.parent_alias = self.root / 'input-alias'
        self.parent_alias.symlink_to(self.inputs, target_is_directory=True)
        self.source = self.inputs / 'original name.raw'
        self.source_bytes = b'\xef\xbb\xbfSynthetic\r\n\xff\x00'
        self.source.write_bytes(self.source_bytes)
        self.body = self.inputs / 'prepared body.md'
        self.body.write_bytes('보고서 archive\r\n'.encode())

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json',
                                 *map(str, args)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn(b'Traceback', result.stderr)
        return json.loads(result.stdout if code == 0 else result.stderr)

    def snapshot(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*')
                if p.is_file() and not p.is_symlink()}

    def captured(self, bundle=None, source=None, key='capture'):
        return self.cli('capture', self.alias if bundle is None else bundle,
                        self.parent_alias / self.source.name if source is None else source,
                        '--id', 'source', '--actor', 'tool/1', '--resource', 'synthetic', '--request-id', key)

    def curated(self, bundle=None, key='curate', expected='absent', code=0):
        args = ['curate', self.alias if bundle is None else bundle, 'rules', '--body', self.parent_alias / self.body.name,
                '--source', 'source', '--actor', 'tool/1']
        if key:
            args += ['--request-id', key]
        if expected:
            args += ['--expect-current', expected]
        return self.cli(*args, code=code)

    def test_alias_cli_reads_writes_replays_and_cas_share_same_lock_and_index(self):
        lock = self.bundle / '.lkw.lock'
        inode = lock.stat().st_ino
        first_capture = self.captured()
        before = self.snapshot()
        self.assertEqual(self.captured(self.bundle, self.source), first_capture)
        self.assertEqual(before, self.snapshot())
        first = self.curated()
        self.assertEqual(self.cli('list', self.alias), self.cli('list', self.bundle))
        self.curated(self.bundle, key=None, expected='r000001')
        before = self.snapshot()
        self.assertEqual(self.curated(self.bundle), first)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.cli('show', self.alias, 'rules')['path'], 'concepts/rules/r000002.md')
        self.assertEqual(self.curated(expected='r000001', key='stale', code=2)['error']['code'], 'precondition_failed')
        with Store(self.bundle) as store, store.lock():
            self.assertEqual(self.curated(key='busy', expected='r000002', code=2)['error']['code'], 'locked')
        self.assertEqual(before, self.snapshot())
        review_args = ['rules', '--revision', 'r000002', '--actor', 'process:test',
                       '--evidence', 'sources/source/content.raw', '--request-id', 'review']
        declared = self.cli('review', self.alias, *review_args)
        before = self.snapshot()
        self.assertEqual(self.cli('review', self.bundle, *review_args), declared)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.cli('inspect-storage', self.alias)['lock']['inode'], inode)
        self.assertEqual(lock.stat().st_ino, inode)
        self.assertEqual(lock.read_bytes(), LOCK_MARKER)

    def test_parent_alias_preserves_final_basename_bytes_and_direct_api(self):
        capture(self.alias, self.parent_alias / self.source.name, 'direct', 'tool/1', 'synthetic',
                '2026-10-29T00:00:00Z', 'direct-capture')
        raw = self.bundle / 'sources/direct/content.raw'
        self.assertEqual(raw.read_bytes(), self.source_bytes)
        provenance = json.loads(raw.with_name('provenance.json').read_bytes())
        self.assertEqual(provenance['original_name'], self.source.name)
        self.assertEqual(read_input(self.parent_alias / self.body.name), self.body.read_bytes())
        self.captured()
        result = self.curated()
        self.assertTrue((self.bundle / result['revision']).read_bytes().endswith(self.body.read_bytes()))

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS literal /tmp alias regression')
    def test_literal_tmp_regular_input_uses_only_owned_unique_file(self):
        handle, name = tempfile.mkstemp(prefix='lsb-paths-owned-', dir='/tmp')
        path = Path(name)
        self.addCleanup(path.unlink, missing_ok=True)
        with os.fdopen(handle, 'wb') as stream:
            stream.write(self.source_bytes)
        self.assertEqual(path.parent, Path('/tmp'))
        self.captured(self.bundle, path, 'tmp-capture')
        self.assertEqual((self.bundle / 'sources/source/content.raw').read_bytes(), self.source_bytes)
        provenance = json.loads((self.bundle / 'sources/source/provenance.json').read_bytes())
        self.assertEqual(provenance['original_name'], path.name)

    def test_loop_dangling_non_directory_and_legacy_resolve_errors_are_structured(self):
        loop = self.root / 'loop'
        loop.symlink_to(loop.name)
        dangling = self.root / 'dangling'
        dangling.symlink_to('missing')
        for path, code in [(loop, 'unsafe_path'), (dangling, 'not_found'), (self.source, 'unsafe_path')]:
            self.assertEqual(self.cli('list', path, code=2)['error']['code'], code)
        with patch.object(Path, 'resolve', side_effect=RuntimeError('Symlink loop from older Python')):
            with self.assertRaises(WikiError) as caught:
                with Store(self.bundle):
                    pass
            self.assertEqual(caught.exception.code, 'unsafe_path')

    def test_resolution_is_once_and_replaced_final_path_still_cannot_be_followed(self):
        original = Path.resolve
        calls = []
        def resolve(path, **kwargs):
            calls.append(path)
            return original(path, **kwargs)
        with patch.object(Path, 'resolve', resolve), Store(self.alias) as store:
            self.assertEqual(os.fstat(store.fd).st_ino, self.bundle.stat().st_ino)
            self.assertEqual(store.read('index.md'), (self.bundle / 'index.md').read_bytes())
        self.assertEqual(calls, [self.alias])
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'keep').write_bytes(b'outside bytes')
        moved = self.root / 'moved'
        def replace_after_resolution(path, **kwargs):
            resolved = original(path, **kwargs)
            if path == self.bundle:
                self.bundle.rename(moved)
                self.bundle.symlink_to(outside, target_is_directory=True)
            return resolved
        with patch.object(Path, 'resolve', replace_after_resolution), self.assertRaises(OSError) as caught:
            with Store(self.bundle):
                self.fail('Final root substitution must not be followed')
        self.assertIn(caught.exception.errno, (errno.ELOOP, errno.ENOTDIR))
        self.assertEqual(sorted(p.name for p in outside.iterdir()), ['keep'])
        self.assertEqual((outside / 'keep').read_bytes(), b'outside bytes')

    def test_init_empty_alias_and_nonempty_alias_no_implicit_tilde_expansion(self):
        empty = self.root / 'empty'
        empty.mkdir()
        link = self.root / 'empty-link'
        link.symlink_to(empty, target_is_directory=True)
        self.cli('init', link)
        self.assertTrue((empty / 'index.md').is_file())
        before = {p.name: p.read_bytes() for p in empty.iterdir() if p.is_file()}
        self.assertEqual(self.cli('init', link, code=2)['error']['code'], 'invalid_input')
        self.assertEqual(before, {p.name: p.read_bytes() for p in empty.iterdir() if p.is_file()})
        literal = self.root / '~'
        literal.mkdir()
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            with Store('~') as store:
                self.assertEqual(os.fstat(store.fd).st_ino, literal.stat().st_ino)
        finally:
            os.chdir(previous)

    def test_internal_and_final_input_links_remain_rejected_and_recall_does_not_follow(self):
        self.captured()
        self.curated()
        final_link = self.parent_alias / 'final-link'
        final_link.symlink_to(self.source)
        self.assertEqual(self.cli('capture', self.alias, final_link, '--id', 'bad', '--actor', 'tool/1',
                                  '--resource', 'synthetic', code=2)['error']['code'], 'unsafe_path')
        body_link = self.parent_alias / 'body-link'
        body_link.symlink_to(self.body)
        self.assertEqual(self.cli('curate', self.alias, 'bad', '--body', body_link, '--source', 'source',
                                  '--actor', 'tool/1', code=2)['error']['code'], 'unsafe_path')
        unrelated = self.bundle / 'unrelated-link'
        unrelated.symlink_to(self.source)
        before, outside = self.snapshot(), self.source.read_bytes()
        for command, args in [('list', []), ('search', ['archive']), ('check', []),
                              ('curate', ['new', '--body', self.body, '--source', 'source', '--actor', 'tool/1'])]:
            self.assertEqual(self.cli(command, self.alias, *args, code=2)['error']['code'], 'unsafe_path')
        self.assertEqual(self.cli('recall', self.alias, 'archive')['matched'], 1)
        self.assertTrue(self.cli('inspect-storage', self.alias)['details']['diagnostics'])
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.source.read_bytes(), outside)
        unrelated.unlink()
        revision = self.bundle / 'concepts/rules/r000001.md'
        revision.unlink()
        revision.symlink_to(self.source)
        self.assertEqual(self.cli('recall', self.alias, 'archive')['excluded']['unavailable'], 1)
        self.assertEqual(self.source.read_bytes(), outside)

    def test_evidence_receipt_source_and_lock_links_keep_existing_boundaries(self):
        self.captured()
        self.curated()
        outside = self.source.read_bytes()
        evidence = self.bundle / 'evidence-link'
        evidence.symlink_to(self.source)
        self.assertEqual(self.cli('review', self.alias, 'rules', '--revision', 'r000001', '--actor', 'process:test',
                                  '--evidence', 'evidence-link', code=2)['error']['code'], 'unsafe_path')
        evidence.unlink()
        raw = self.bundle / 'sources/source/content.raw'
        raw.unlink()
        raw.symlink_to(self.source)
        self.assertEqual(self.curated(key='unsafe-source', expected='r000001', code=2)['error']['code'], 'unsafe_path')
        raw.unlink()
        raw.write_bytes(self.source_bytes)
        receipt = self.bundle / '.lkw-requests/curate/result.json'
        receipt.unlink()
        receipt.symlink_to(self.source)
        self.assertEqual(self.curated(code=2)['error']['code'], 'recovery_required')
        lock = self.bundle / '.lkw.lock'
        lock.unlink()  # Synthetic unsafe-lock fixture, not product recovery.
        lock.symlink_to(self.source)
        self.assertEqual(self.curated(key='unsafe-lock', expected='r000001', code=2)['error']['code'], 'unsafe_path')
        self.assertEqual(self.source.read_bytes(), outside)

    def test_alias_rebinding_after_open_does_not_redirect_descriptor_reads(self):
        outside = self.root / 'other-root'
        outside.mkdir()
        (outside / 'index.md').write_bytes(b'outside must stay untouched')
        original = (self.bundle / 'index.md').read_bytes()
        with Store(self.alias) as store:
            self.alias.unlink()
            self.alias.symlink_to(outside, target_is_directory=True)
            self.assertEqual(store.read('index.md'), original)
            self.assertEqual(os.fstat(store.fd).st_ino, self.bundle.stat().st_ino)
        self.assertEqual((outside / 'index.md').read_bytes(), b'outside must stay untouched')
