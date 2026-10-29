"""Reserved receipt-root blockers are visible without following or changing them."""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_knowledge_wiki.inspection import inspect_storage
from local_knowledge_wiki.storage import Store, capture, init


class InspectionNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'wiki'
        init(self.bundle)
        self.source = self.root / 'source'
        self.source.write_bytes(b'synthetic source')
        capture(self.bundle, self.source, 'source', 'tool/1', 'synthetic', '2026-10-29T00:00:00Z')
        self.namespace = self.bundle / '.lkw-requests'

    def snapshot(self, root):
        values = {}
        for path in root.rglob('*'):
            info = path.lstat()
            value = (info.st_mode, info.st_dev, info.st_ino)
            if stat.S_ISREG(info.st_mode):
                value += (path.read_bytes(),)
            elif stat.S_ISLNK(info.st_mode):
                value += (os.readlink(path),)
            values[str(path.relative_to(root))] = value
        return values

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json',
                                 *map(str, args)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn(b'Traceback', result.stderr)
        return json.loads((result.stdout if code == 0 else result.stderr).decode('utf-8', errors='strict'))

    def test_non_directory_reserved_roots_block_keyed_writes_and_are_diagnosed_read_only(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'external-request').mkdir()
        (outside / 'external-request/intent.json').write_bytes(b'outside bytes')
        for kind in ('regular_file', 'symlink', 'fifo'):
            with self.subTest(kind=kind):
                if kind == 'regular_file':
                    self.namespace.write_bytes(b'reserved root blocker')
                elif kind == 'symlink':
                    self.namespace.symlink_to(outside, target_is_directory=True)
                else:
                    os.mkfifo(self.namespace)
                before, external = self.snapshot(self.bundle), self.snapshot(outside)
                failure = self.cli('capture', self.bundle, self.source, '--id', 'new', '--actor', 'tool/1',
                                   '--resource', 'synthetic', '--request-id', 'key', code=2)
                self.assertEqual(failure['error']['code'], 'recovery_required')
                self.assertEqual(before, self.snapshot(self.bundle))
                report = self.cli('inspect-storage', self.bundle)
                self.assertEqual(report['receipts'].get('namespace'), {'state': 'invalid', 'type': kind})
                self.assertIsNone(report['receipts']['total'])
                self.assertEqual(report['receipts']['checked'], 0)
                self.assertFalse(report['scan']['complete'])
                self.assertEqual(report['index']['state'], 'valid')
                self.assertTrue(any(d['path'] == '.lkw-requests' and d['code'] == 'unsafe_path'
                                    and kind in d['message'] for d in report['details']['diagnostics']))
                self.assertEqual(before, self.snapshot(self.bundle))
                self.assertEqual(external, self.snapshot(outside))
                self.namespace.unlink()  # Remove only this synthetic test artifact.

    def test_absent_and_real_directory_have_distinct_available_states(self):
        before = self.snapshot(self.bundle)
        absent = self.cli('inspect-storage', self.bundle)
        self.assertEqual(absent['receipts'].get('namespace'), {'state': 'absent'})
        self.assertEqual(absent['receipts']['total'], 0)
        self.assertEqual(before, self.snapshot(self.bundle))
        self.namespace.mkdir()
        before = self.snapshot(self.bundle)
        empty = self.cli('inspect-storage', self.bundle)
        self.assertEqual(empty['receipts'].get('namespace'), {'state': 'directory', 'type': 'directory'})
        self.assertEqual(empty['receipts']['total'], 0)
        self.assertEqual(empty['details']['diagnostics'], [])
        self.assertTrue(empty['scan']['complete'])
        self.assertEqual(before, self.snapshot(self.bundle))
        self.cli('capture', self.bundle, self.source, '--id', 'new', '--actor', 'tool/1',
                 '--resource', 'synthetic', '--request-id', 'key')
        before = self.snapshot(self.bundle)
        available = self.cli('inspect-storage', self.bundle)
        self.assertEqual(available['receipts']['states'], {'self_consistent': 1})
        self.assertEqual(before, self.snapshot(self.bundle))

    def test_inaccessible_reserved_directory_is_unavailable_not_healthy_zero(self):
        self.namespace.mkdir()
        real_open = os.open
        def inaccessible(path, flags, *args, **kwargs):
            if path == '.lkw-requests' and flags & os.O_DIRECTORY:
                raise PermissionError('synthetic inaccessible receipt directory')
            return real_open(path, flags, *args, **kwargs)
        before = self.snapshot(self.bundle)
        with patch('local_knowledge_wiki.inspection.os.open', inaccessible):
            report = inspect_storage(self.bundle)
        self.assertEqual(report['receipts'].get('namespace'), {'state': 'unavailable', 'type': 'directory'})
        self.assertIsNone(report['receipts']['total'])
        self.assertFalse(report['scan']['complete'])
        self.assertEqual(report['index']['state'], 'valid')
        self.assertTrue(any(d['path'] == '.lkw-requests' for d in report['details']['diagnostics']))
        self.assertEqual(before, self.snapshot(self.bundle))
