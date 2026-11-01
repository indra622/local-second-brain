"""Synthetic byte boundaries, allocation guards, and no-effect rejections."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_knowledge_wiki import limits
from local_knowledge_wiki.cli import curate, main, review
from local_knowledge_wiki.errors import WikiError
from local_knowledge_wiki.format import parse
from local_knowledge_wiki.limits import bounded_read
from local_knowledge_wiki.requests import load
from local_knowledge_wiki.storage import Store, capture, init, read_input


AT = '2026-01-01T00:00:00+00:00'


class InputLimitsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'wiki'
        init(self.bundle)
        self.source = self.root / 'input'
        self.source.write_bytes(b'evidence')
        capture(self.bundle, self.source, 'source', 'tool/1', 'synthetic', AT)
        self.body = self.root / 'body'
        self.body.write_bytes(b'body')

    def snapshot(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes()
                for p in self.bundle.rglob('*') if p.is_file()}

    def too_large(self, call):
        with self.assertRaises(WikiError) as caught:
            call()
        self.assertEqual(caught.exception.code, 'input_too_large')

    def curate(self, request=None):
        return curate(self.bundle, 'note', self.body, ['source'], 'tool/1', AT,
                      'Concept', None, 'stable', None, request, 'absent')

    def test_raw_exact_limit_and_plus_one_sparse_rejection_before_read(self):
        # A small injected budget proves inclusive semantics without a 256 MiB fixture.
        self.source.write_bytes(b'a' * 31 + b'\xff')
        self.assertEqual(read_input(self.source, max_bytes=32), self.source.read_bytes())
        with self.source.open('r+b') as stream:
            stream.truncate(limits.SOURCE_BYTES + 1)
        before = self.snapshot()
        with patch('local_knowledge_wiki.storage.bounded_read', side_effect=AssertionError('allocated')):
            self.too_large(lambda: capture(self.bundle, self.source, 'new', 'a/1', 'synthetic', AT, 'key'))
        self.assertEqual(before, self.snapshot())

    def test_bounded_growth_and_short_reads(self):
        class Growing:
            def __init__(self):
                self.used = 0
            def read(self, count):
                self.assert_count = count
                if count < 0:
                    raise AssertionError('unbounded allocation')
                self.used += min(count, 3)
                return b'x' * min(count, 3)
        stream = Growing()
        self.too_large(lambda: bounded_read(stream, 32, 'growing'))
        self.assertEqual(stream.used, 33)
        self.assertEqual(bounded_read(io.BytesIO(b'x' * 32), 32, 'exact'), b'x' * 32)
        # fstat reports a small file, but the opened stream grows past its budget.
        class FileGrowth(Growing):
            def __enter__(self):
                return self
            def __exit__(self, *args):
                os.close(self.fd)
            def fileno(self):
                return self.fd
        stream = FileGrowth()
        def fdopen(fd, mode):
            stream.fd = fd
            return stream
        with Store(self.root) as store, patch('local_knowledge_wiki.storage.os.fdopen', fdopen):
            self.too_large(lambda: store.read('input', max_bytes=32))
        self.assertEqual(stream.used, 33)

    def test_body_utf8_byte_boundary_and_no_intent_on_overflow(self):
        with patch('local_knowledge_wiki.cli.BODY_BYTES', 6):
            self.body.write_bytes('가나'.encode())
            self.curate()
            before = self.snapshot()
            self.body.write_bytes('가나x'.encode())
            self.too_large(lambda: self.curate('overflow'))
            self.assertEqual(before, self.snapshot())
            # A byte budget does not truncate an incomplete UTF-8 character.
            self.body.write_bytes('가나'.encode()[:-1])
            with self.assertRaises(UnicodeDecodeError):
                self.curate('invalid-utf8')
            self.assertEqual(before, self.snapshot())

    def test_metadata_and_stored_body_boundaries_before_parser(self):
        header = b'type: Concept\n'
        with patch('local_knowledge_wiki.limits.METADATA_BYTES', len(header)):
            path = self.bundle / 'note.md'
            path.write_bytes(b'---\n' + header + b'---\nbody')
            with Store(self.bundle) as store:
                self.assertEqual(store.read('note.md'), path.read_bytes())
                path.write_bytes(b'---\n' + header + b' \n---\nbody')
                self.too_large(lambda: store.read('note.md'))
        with patch('local_knowledge_wiki.format.METADATA_BYTES', len(header)):
            self.assertEqual(parse('---\n' + header.decode() + '---\nbody')[1], 'body')
            with patch('local_knowledge_wiki.format.yaml.load', side_effect=AssertionError('parsed')):
                self.too_large(lambda: parse('---\n' + header.decode() + ' \n---\nbody'))
        path.write_bytes(b'---\n' + header + b'---\n12345')
        with patch('local_knowledge_wiki.limits.BODY_BYTES', 4), Store(self.bundle) as store:
            self.too_large(lambda: store.read('note.md'))

    def test_receipt_limit_checked_before_allocation_and_exact_fit(self):
        path = self.bundle / '.lkw-requests/key/result.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'null')
        with patch('local_knowledge_wiki.requests.RECEIPT_BYTES', 4), Store(self.bundle) as store:
            self.assertIsNone(load(store, '.lkw-requests/key/result.json'))
            path.write_bytes(b'null ')
            with patch('local_knowledge_wiki.storage.bounded_read', side_effect=AssertionError('allocated')):
                self.too_large(lambda: load(store, '.lkw-requests/key/result.json'))
        with path.open('wb') as stream:
            stream.truncate(limits.RECEIPT_BYTES + 1)
        with Store(self.bundle) as store, patch('local_knowledge_wiki.storage.bounded_read', side_effect=AssertionError('allocated')):
            self.too_large(lambda: load(store, '.lkw-requests/key/result.json'))

    def test_real_index_body_and_frontmatter_boundaries(self):
        path = self.bundle / 'boundary.md'
        header = b'---\ntype: Concept\n---\n'
        with path.open('wb') as stream:
            stream.write(header)
            stream.truncate(len(header) + limits.BODY_BYTES)
        with Store(self.bundle) as store:
            self.assertEqual(len(store.read('boundary.md')), len(header) + limits.BODY_BYTES)
            with path.open('ab') as stream:
                stream.write(b'x')
            self.too_large(lambda: store.read('boundary.md'))
        # A comment is valid YAML and its encoded LF counts toward metadata bytes.
        metadata = b'type: Concept\n#' + b'x' * (limits.METADATA_BYTES - 16) + b'\n'
        self.assertEqual(len(metadata), limits.METADATA_BYTES)
        path.write_bytes(b'---\n' + metadata + b'---\n')
        with Store(self.bundle) as store:
            self.assertEqual(len(store.read('boundary.md')), limits.METADATA_BYTES + 8)
            path.write_bytes(b'---\n' + metadata + b' \n---\n')
            self.too_large(lambda: store.read('boundary.md'))
        index = self.bundle / 'index.md'
        with index.open('wb') as stream:
            stream.truncate(limits.INDEX_BYTES)
        with Store(self.bundle) as store:
            self.assertEqual(len(store.read('index.md')), limits.INDEX_BYTES)
            with index.open('ab') as stream:
                stream.write(b'x')
            self.too_large(lambda: store.read('index.md'))

    def test_oversized_receipt_replay_requires_inspection_without_effects(self):
        self.curate('replay')
        receipt = self.bundle / '.lkw-requests/replay/result.json'
        with receipt.open('wb') as stream:
            stream.truncate(limits.RECEIPT_BYTES + 1)
        before = self.snapshot()
        with self.assertRaises(WikiError) as caught:
            self.curate('replay')
        self.assertEqual(caught.exception.code, 'recovery_required')
        self.assertEqual(before, self.snapshot())

    def test_fifo_directory_symlink_never_read(self):
        fifo = self.root / 'fifo'
        os.mkfifo(fifo)
        link = self.root / 'link'
        link.symlink_to(self.source)
        for path in (fifo, self.root, link):
            with self.subTest(path=path), self.assertRaises((WikiError, OSError)):
                read_input(path)

    def test_writer_index_metadata_and_receipt_preflight_have_no_effects(self):
        before = self.snapshot()
        with patch('local_knowledge_wiki.cli.INDEX_BYTES', 1):
            self.too_large(lambda: self.curate('index-limit'))
        self.assertEqual(before, self.snapshot())
        with patch('local_knowledge_wiki.format.METADATA_BYTES', 1):
            self.too_large(lambda: self.curate('metadata-limit'))
        self.assertEqual(before, self.snapshot())
        self.curate()
        before = self.snapshot()
        with patch('local_knowledge_wiki.requests.RECEIPT_BYTES', 1):
            self.too_large(lambda: review(self.bundle, 'note', 'r000001', 'human:test',
                                         'sources/source/content.raw', 'receipt-limit', AT))
        self.assertEqual(before, self.snapshot())

    def test_platform_guard_human_json_help_and_missing_capability(self):
        for mode in ('legacy', 'json'):
            output = io.StringIO()
            destination = self.root / ('unsupported-' + mode)
            with patch('local_knowledge_wiki.platform.sys.platform', 'win32'), contextlib.redirect_stderr(output):
                self.assertEqual(main(['--error-format', mode, 'init', str(destination)]), 2)
            self.assertFalse(destination.exists())
            if mode == 'json':
                self.assertEqual(json.loads(output.getvalue())['error']['code'], 'unsupported_platform')
            else:
                self.assertIn('Unsupported platform', output.getvalue())
        with patch('local_knowledge_wiki.platform.sys.platform', 'win32'), patch('local_knowledge_wiki.cli.Store') as store:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['recall', str(self.bundle), 'body']), 2)
            store.assert_not_called()
        with patch('local_knowledge_wiki.platform.os.supports_dir_fd', set()):
            with self.assertRaises(WikiError) as caught:
                init(self.root / 'missing-capability')
            self.assertEqual(caught.exception.code, 'unsupported_platform')
        with patch('local_knowledge_wiki.platform.sys.platform', 'win32'), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(['--help'])
            self.assertEqual(caught.exception.code, 0)
