"""Synthetic owned staging, persistent flock and read-only inventory tests."""

import builtins
import errno
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_knowledge_wiki.cli import curate
from local_knowledge_wiki.inspection import inspect_storage
from local_knowledge_wiki.requests import ROOT, digest, encoded
from local_knowledge_wiki.storage import LOCK_MARKER, Store, WikiError, capture, init


class StorageInterruptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'wiki'
        init(self.bundle)
        self.source = self.root / 'source'
        self.source.write_bytes(b'synthetic')
        self.body = self.root / 'body'
        self.body.write_text('archive 보고서')
        capture(self.bundle, self.source, 'source', 'tool/1', 'synthetic', '2026-10-29T00:00:00Z')

    def curate(self, key=None):
        return curate(self.bundle, 'rules', self.body, ['source'], 'tool/1', '2026-10-29T00:00:00Z',
                      'Concept', '보고서', 'draft', None, key)

    def snapshot(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*')
                if p.is_file() and not p.is_symlink()}

    def error(self, code, call):
        with self.assertRaises(WikiError) as caught:
            call()
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_fixed_and_random_collisions_preserved_and_retries_bounded(self):
        fixed = self.bundle / '.lkw-index.tmp'
        fixed.write_bytes(b'old fixed bytes')
        random = self.bundle / ('.lkw-index.' + 'a' * 32 + '.tmp')
        random.write_bytes(b'old random bytes')
        with patch('local_knowledge_wiki.storage.secrets.token_hex', side_effect=['a' * 32, 'b' * 32]):
            self.assertTrue(self.curate().endswith('r000001.md'))
        self.assertEqual(fixed.read_bytes(), b'old fixed bytes')
        self.assertEqual(random.read_bytes(), b'old random bytes')
        before = self.snapshot()
        with patch('local_knowledge_wiki.storage.secrets.token_hex', return_value='a' * 32) as token:
            self.error('already_exists', self.curate)
            self.assertEqual(token.call_count, 10)
        self.assertEqual(before, self.snapshot())

    def test_stage_partial_write_and_sync_fail_before_revision_with_pending_key(self):
        real_write, real_sync, real_open = os.write, os.fsync, os.open
        for phase in ('write', 'sync'):
            stage_handles, failures = set(), []
            def opened(path, *args, **kwargs):
                handle = real_open(path, *args, **kwargs)
                if isinstance(path, str) and path.startswith('.lkw-index.'):
                    stage_handles.add(handle)
                return handle
            def write(handle, data):
                if phase == 'write':
                    real_write(handle, bytes(data[:3]))
                    failures.append('write')
                    raise OSError(errno.ENOSPC, 'partial stage')
                return real_write(handle, data)
            def sync(handle):
                if phase == 'sync' and handle in stage_handles:
                    failures.append('sync')
                    raise OSError(errno.EIO, 'stage sync')
                return real_sync(handle)
            before_index = (self.bundle / 'index.md').read_bytes()
            # Intent writes use Store.create's stream, not this owned stage descriptor.
            with patch('local_knowledge_wiki.storage.os.open', opened), patch('local_knowledge_wiki.storage.os.write', write), patch('local_knowledge_wiki.storage.os.fsync', sync):
                self.error('recovery_required', lambda: self.curate('stage-' + phase))
            self.assertEqual(failures, [phase])
            self.assertTrue((self.bundle / ROOT / ('stage-' + phase) / 'intent.json').exists())
            self.assertEqual(list(self.bundle.glob('concepts/rules/r*.md')), [])
            self.assertEqual((self.bundle / 'index.md').read_bytes(), before_index)
            self.assertEqual(list(self.bundle.glob('.lkw-index.*.tmp')), [])
            before = self.snapshot()
            self.error('recovery_required', lambda: self.curate('stage-' + phase))
            self.assertEqual(before, self.snapshot())

    def test_stage_sync_unkeyed_and_owned_cleanup_after_substitution(self):
        with Store(self.bundle) as store:
            before = self.snapshot()
            with patch('local_knowledge_wiki.storage.os.fsync', side_effect=OSError(errno.EIO, 'sync')):
                with self.assertRaises(OSError), store.stage_index(b'index'):
                    self.fail('stage should not be yielded')
            self.assertEqual(before, self.snapshot())
            with store.stage_index(b'index') as name:
                path = self.bundle / name
                path.unlink()
                path.write_bytes(b'replacement')
                self.error('concurrent_change', lambda: store.replace_index((self.bundle / 'index.md').read_bytes(), b'index'))
            self.assertEqual(path.read_bytes(), b'replacement')

    def test_before_and_after_rename_and_directory_sync_never_delete_revision(self):
        real_replace, real_sync = os.replace, os.fsync
        for phase in ('before', 'after', 'directory-sync'):
            old = (self.bundle / 'index.md').read_bytes()
            published = []
            def replace(*args, **kwargs):
                if phase == 'before':
                    raise OSError(errno.EIO, 'before rename')
                real_replace(*args, **kwargs)
                published.append(True)
                if phase == 'after':
                    raise OSError(errno.EIO, 'after actual rename')
            def sync(handle):
                if phase == 'directory-sync' and published and stat.S_ISDIR(os.fstat(handle).st_mode):
                    raise OSError(errno.EIO, 'post-publication root sync')
                real_sync(handle)
            with patch('local_knowledge_wiki.storage.os.replace', replace), patch('local_knowledge_wiki.storage.os.fsync', sync):
                self.error('recovery_required', lambda: self.curate('rename-' + phase))
            revisions = sorted(self.bundle.glob('concepts/rules/r*.md'))
            self.assertEqual(len(revisions), ('before', 'after', 'directory-sync').index(phase) + 1)
            current = (self.bundle / 'index.md').read_bytes()
            if phase == 'before':
                self.assertEqual(current, old)
            else:
                self.assertIn(revisions[-1].name.encode(), current)
            self.assertFalse((self.bundle / ROOT / ('rename-' + phase) / 'result.json').exists())
            before = self.snapshot()
            self.error('recovery_required', lambda: self.curate('rename-' + phase))
            self.assertEqual(before, self.snapshot())

    def holder(self, code=None):
        script = code or '''
import sys
from local_knowledge_wiki.storage import Store
with Store(sys.argv[1]) as store, store.lock():
    print('ready', flush=True)
    sys.stdin.readline()
'''
        process = subprocess.Popen([sys.executable, '-u', '-c', script, str(self.bundle)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.reap, process)
        self.assertEqual(process.stdout.readline(), b'ready\n')
        return process

    def reap(self, process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)

    def test_killed_initialized_holder_releases_same_inode_and_old_writer_refuses(self):
        lock = self.bundle / '.lkw.lock'
        original_inode = lock.stat().st_ino
        process = self.holder()
        with Store(self.bundle) as store:
            self.error('locked', lambda: self.acquire(store))
        self.assertEqual(inspect_storage(self.bundle)['lock']['state'], 'recognized_busy')
        process.kill()
        process.communicate(timeout=10)
        with Store(self.bundle) as store, store.lock() as handle:
            self.assertFalse(os.get_inheritable(handle))
            self.assertEqual(os.fstat(handle).st_ino, original_inode)
        self.assertEqual(lock.stat().st_ino, original_inode)
        self.assertEqual(lock.read_bytes(), LOCK_MARKER)
        with self.assertRaises(FileExistsError):
            os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)

    def acquire(self, store):
        with store.lock():
            pass

    def test_live_legacy_writer_and_unknown_bootstraps_remain_untouched(self):
        lock = self.bundle / '.lkw.lock'
        lock.unlink()  # Synthetic migration fixture, never product recovery.
        process = self.holder('''
import os,sys
path=os.path.join(sys.argv[1],'.lkw.lock')
fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o644)
os.write(fd,b'active local CLI write\\n')
print('ready',flush=True)
sys.stdin.readline()
os.close(fd)
''')
        before = self.snapshot()
        with Store(self.bundle) as store:
            self.error('recovery_required', lambda: self.acquire(store))
        self.assertIsNone(process.poll())
        self.assertEqual(before, self.snapshot())
        self.reap(process)
        for content in (b'', b'lkw:flock:', b'lkw:flock:v2\n', LOCK_MARKER + b'extra'):
            lock.write_bytes(content)
            before = self.snapshot()
            with Store(self.bundle) as store:
                self.error('recovery_required', lambda: self.acquire(store))
            self.assertEqual(before, self.snapshot())

    def test_unsafe_locks_do_not_hang_follow_or_delete(self):
        lock = self.bundle / '.lkw.lock'
        for kind in ('symlink', 'directory', 'fifo', 'hardlink'):
            lock.unlink()
            if kind == 'symlink':
                lock.symlink_to(self.source)
            elif kind == 'directory':
                lock.mkdir()
            elif kind == 'fifo':
                os.mkfifo(lock)
            else:
                os.link(self.source, lock)
            with Store(self.bundle) as store:
                self.error('unsafe_path', lambda: self.acquire(store))
            self.assertTrue(os.path.lexists(lock))
            self.assertEqual(self.source.read_bytes(), b'synthetic')
            if kind == 'directory':
                lock.rmdir()
                lock.touch()
            elif kind in ('symlink', 'fifo'):
                lock.unlink()
                lock.touch()

    def test_lock_substitution_and_bootstrap_failure_fail_closed(self):
        from local_knowledge_wiki.storage import flock
        lock = self.bundle / '.lkw.lock'
        def substitute(handle, shared=False):
            flock(handle, shared)
            lock.unlink()
            lock.write_bytes(LOCK_MARKER)
        with Store(self.bundle) as store, patch('local_knowledge_wiki.storage.flock', substitute):
            self.error('unsafe_path', lambda: self.acquire(store))
        self.assertEqual(lock.read_bytes(), LOCK_MARKER)
        lock.unlink()
        before = (self.bundle / 'index.md').read_bytes()
        with Store(self.bundle) as store, patch('local_knowledge_wiki.storage.write_all', side_effect=OSError(errno.EIO, 'bootstrap')):
            with self.assertRaises(OSError):
                self.acquire(store)
        self.assertEqual(lock.read_bytes(), b'')
        self.assertEqual((self.bundle / 'index.md').read_bytes(), before)
        with Store(self.bundle) as store:
            self.error('recovery_required', lambda: self.acquire(store))

    def test_unsupported_flock_is_explicit_and_init_nonempty_does_not_create_lock(self):
        real_import = builtins.__import__
        def importer(name, *args, **kwargs):
            if name == 'fcntl':
                raise ImportError('synthetic unsupported capability')
            return real_import(name, *args, **kwargs)
        with Store(self.bundle) as store, patch('builtins.__import__', importer):
            self.error('recovery_required', lambda: self.acquire(store))
        target = self.root / 'nonempty'
        target.mkdir()
        (target / 'keep').write_text('user bytes')
        with self.assertRaises(WikiError):
            init(target)
        self.assertEqual(sorted(p.name for p in target.iterdir()), ['keep'])

    def test_inspection_history_receipt_evidence_and_absent_lock_are_read_only(self):
        self.curate('first')
        self.curate()
        self.curate('third')
        before = self.snapshot()
        report = inspect_storage(self.bundle)
        self.assertEqual(report['consistency'], 'shared_lock_held')
        self.assertEqual(report['revisions']['non_current'], 2)
        self.assertEqual(report['revisions']['non_current_with_completion_evidence'], 1)
        self.assertEqual(report['revisions']['unclassified_non_current'], 1)
        self.assertEqual(report['receipts']['states'], {'self_consistent': 2})
        self.assertEqual(before, self.snapshot())
        (self.bundle / '.lkw.lock').unlink()  # Inspect absent marker without initializing it.
        before = self.snapshot()
        report = inspect_storage(self.bundle)
        self.assertEqual(report['lock']['state'], 'absent')
        self.assertEqual(report['consistency'], 'best_effort')
        self.assertEqual(before, self.snapshot())

    def test_inspection_invalid_pending_corrupt_unsafe_and_size_limit(self):
        self.curate('done')
        pending = self.bundle / ROOT / 'pending'
        pending.mkdir()
        intent = {'version': 1, 'command': 'curate', 'fingerprint': 'a' * 64}
        (pending / 'intent.json').write_bytes(encoded(intent))
        huge = self.bundle / ROOT / 'huge'
        huge.mkdir()
        with (huge / 'intent.json').open('wb') as stream:
            stream.truncate(8000001)
        (self.bundle / 'index.md').write_text('invalid')
        (self.bundle / 'unsafe-link').symlink_to(self.source)
        result_path = self.bundle / ROOT / 'done/result.json'
        record = json.loads(result_path.read_bytes())
        record['artifacts'] = {'../../source': digest(self.source.read_bytes())}
        record.pop('checksum')
        record['checksum'] = digest(encoded(record))
        result_path.write_bytes(encoded(record))
        before = self.snapshot()
        reads = []
        original_read = Store.read
        def read(store, path, **kwargs):
            reads.append(path)
            return original_read(store, path, **kwargs)
        with patch.object(Store, 'read', read):
            report = inspect_storage(self.bundle)
        self.assertEqual(report['index']['state'], 'invalid_or_unavailable')
        self.assertIsNone(report['revisions']['non_current'])
        self.assertEqual(report['receipts']['states'], {'corrupt': 2, 'pending': 1})
        self.assertTrue(any(d['code'] == 'unsafe_path' for d in report['details']['diagnostics']))
        self.assertNotIn('../../source', reads)
        self.assertEqual(before, self.snapshot())

    def test_inspection_shared_lock_excludes_writers_and_bounds_details(self):
        self.curate()
        from local_knowledge_wiki.inspection import read_receipt
        original_read = Store.read
        attempts = []
        def read(store, path, **kwargs):
            if path == 'index.md':
                with Store(self.bundle) as writer:
                    self.error('locked', lambda: self.acquire(writer))
                attempts.append(True)
            return original_read(store, path, **kwargs)
        for i in range(110):
            (self.bundle / f'.lkw-index.{i:032x}.tmp').write_bytes(b'old')
        with patch.object(Store, 'read', read):
            report = inspect_storage(self.bundle)
        self.assertTrue(attempts)
        self.assertEqual(len(report['details']['staging']), 100)
        self.assertEqual(report['omitted']['staging'], 10)
        self.assertEqual(report['staging']['total'], 110)
        big = self.bundle / 'big'
        with big.open('wb') as stream:
            stream.truncate(8000001)
        real_fdopen = os.fdopen
        class GuardedStream:
            def __init__(self, handle, *args):
                self.stream = real_fdopen(handle, *args)
            def __enter__(self):
                return self
            def fileno(self):
                return self.stream.fileno()
            def read(self, *args):
                raise AssertionError('Oversize receipt must be rejected before any read allocation')
            def __exit__(self, *args):
                self.stream.close()
        with Store(self.bundle) as store, patch('local_knowledge_wiki.storage.os.fdopen', GuardedStream):
            with self.assertRaises(WikiError):
                read_receipt(store, 'big')

    def test_inspection_cli_strict_unicode_json_and_machine_errors(self):
        self.curate()
        try:
            os.symlink(self.source, os.fsencode(self.bundle) + b'/invalid-\xff')
        except OSError as exc:
            if exc.errno != errno.EILSEQ:
                raise
            # macOS may reject invalid-UTF8 filenames; still exercise real Unicode stdout.
            (self.bundle / '보고서-link').symlink_to(self.source)
        command = [sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json', 'inspect-storage', str(self.bundle)]
        result = subprocess.run(command, capture_output=True, timeout=10,
                                env={**os.environ, 'PYTHONIOENCODING': 'utf-8:strict'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout.decode('utf-8'))['details']['diagnostics'])
        failed = subprocess.run(command[:-1], capture_output=True, timeout=10)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(json.loads(failed.stderr)['error']['code'], 'arguments')

    def test_unkeyed_stage_failure_has_no_revision_and_inspection_missing_current(self):
        before = self.snapshot()
        with patch('local_knowledge_wiki.storage.write_all', side_effect=OSError(errno.ENOSPC, 'stage')) as failure:
            with self.assertRaises(OSError):
                self.curate()
            self.assertEqual(failure.call_count, 1)
        self.assertEqual(before, self.snapshot())
        path = self.curate('complete')
        (self.bundle / path).unlink()
        before = self.snapshot()
        report = inspect_storage(self.bundle)
        self.assertEqual(report['index']['state'], 'valid')
        self.assertEqual(report['index']['missing_current'], 1)
        self.assertEqual(report['receipts']['states'], {'corrupt': 1})
        self.assertEqual(before, self.snapshot())

    def test_lock_bootstrap_partial_write_is_preserved_and_empty_contender_refuses(self):
        lock = self.bundle / '.lkw.lock'
        lock.unlink()
        real_write = os.write
        def partial(handle, data):
            real_write(handle, bytes(data[:4]))
            raise OSError(errno.EIO, 'partial bootstrap')
        with Store(self.bundle) as store, patch('local_knowledge_wiki.storage.os.write', partial):
            with self.assertRaises(OSError):
                self.acquire(store)
        self.assertEqual(lock.read_bytes(), LOCK_MARKER[:4])
        before = self.snapshot()
        with Store(self.bundle) as store:
            self.error('recovery_required', lambda: self.acquire(store))
        self.assertEqual(before, self.snapshot())

    def test_inspection_receipt_and_traversal_caps_are_explicit(self):
        for i in range(4):
            self.curate('receipt-' + str(i))
        with patch('local_knowledge_wiki.inspection.RECEIPT_LIMIT', 2):
            report = inspect_storage(self.bundle)
        self.assertEqual(report['receipts']['checked'], 2)
        self.assertEqual(report['receipts']['unchecked'], 2)
        self.assertEqual(report['omitted']['receipts'], 2)
        with patch('local_knowledge_wiki.inspection.ENTRY_LIMIT', 2):
            report = inspect_storage(self.bundle)
        self.assertFalse(report['scan']['complete'])
        self.assertLessEqual(report['scan']['visited'], 2)

    def test_killed_keyed_stage_releases_lock_but_never_replays_pending_effects(self):
        inode = (self.bundle / '.lkw.lock').stat().st_ino
        process = self.holder('''
import sys
from contextlib import contextmanager
from pathlib import Path
from local_knowledge_wiki.cli import curate
from local_knowledge_wiki.storage import Store
original=Store.stage_index
@contextmanager
def stage(store,data):
    with original(store,data) as name:
        print('ready',flush=True)
        sys.stdin.readline()
        yield name
Store.stage_index=stage
bundle=Path(sys.argv[1])
curate(bundle,'rules',bundle.parent/'body',['source'],'tool/1','2026-10-29T00:00:00Z',
       'Concept','보고서','draft',None,'killed')
''')
        process.kill()
        process.communicate(timeout=10)
        self.assertEqual((self.bundle / '.lkw.lock').stat().st_ino, inode)
        self.assertEqual(list(self.bundle.glob('concepts/rules/r*.md')), [])
        before = self.snapshot()
        inventory = inspect_storage(self.bundle)
        self.assertEqual(inventory['consistency'], 'shared_lock_held')
        self.assertEqual(inventory['receipts']['states'], {'pending': 1})
        self.assertEqual(inventory['staging']['total'], 1)
        self.error('recovery_required', lambda: self.curate('killed'))
        self.assertEqual(before, self.snapshot())

    def test_inspection_inaccessible_directory_and_legacy_lock_are_qualified(self):
        self.curate()
        (self.bundle / 'unavailable').mkdir()
        original = os.scandir
        def scandir(fd):
            with Store(self.bundle) as store:
                with store.parent('unavailable/file') as (parent, _):
                    unavailable = os.fstat(parent)
            if os.fstat(fd).st_ino == unavailable.st_ino:
                raise PermissionError(errno.EACCES, 'synthetic inaccessible directory')
            return original(fd)
        with patch('local_knowledge_wiki.inspection.os.scandir', scandir):
            inventory = inspect_storage(self.bundle)
        self.assertFalse(inventory['scan']['complete'])
        self.assertEqual(inventory['revisions']['total'], 1)
        self.assertTrue(any('unavailable' in d['path'] for d in inventory['details']['diagnostics']))
        (self.bundle / '.lkw.lock').write_bytes(b'active local CLI write\n')
        before = self.snapshot()
        inventory = inspect_storage(self.bundle)
        self.assertEqual(inventory['lock']['state'], 'legacy_or_unknown')
        self.assertEqual(inventory['consistency'], 'best_effort')
        self.assertEqual(before, self.snapshot())
