"""Synthetic replay/CAS transitions and injected partial-write boundaries."""

import contextlib
import errno
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_knowledge_wiki.cli import curate, main, review
from local_knowledge_wiki.requests import ROOT, digest, encoded
from local_knowledge_wiki.storage import Store, WikiError, capture, init


AT = '2026-10-29T00:00:00+00:00'


class SafeWritesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'wiki'
        init(self.bundle)
        self.source = self.root / 'input'
        self.source.write_bytes(b'synthetic source\r\n\xff')
        self.body = self.root / 'body'
        self.body.write_text('archive 보고서 규칙\n')
        capture(self.bundle, self.source, 'source', 'tool/1', 'synthetic', AT)

    def curate(self, key=None, expected=None, **changes):
        args = dict(root=self.bundle, concept_id='rules', body_file=self.body, sources=['source'],
                    actor='tool/1', now=AT, kind='Concept', title=None, status='draft', stale_after=None,
                    request_id=key, expect_current=expected)
        args.update(changes)
        return curate(**args)

    def review(self, key=None, **changes):
        args = dict(root=self.bundle, concept_id='rules', revision='r000001', actor='process:test',
                    evidence='sources/source/content.raw', request_id=key)
        args.update(changes)
        return review(**args)

    def snapshot(self, receipts=True):
        return {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*')
                if p.is_file() and not p.is_symlink()
                and (receipts or ROOT not in p.parts)}

    def error(self, code, call):
        with self.assertRaises(WikiError) as caught:
            call()
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def cli(self, *args, code=0):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                actual = main(['--error-format', 'json', *map(str, args)])
            except SystemExit as exc:
                actual = exc.code
        self.assertEqual(actual, code, out.getvalue() + err.getvalue())
        return json.loads(out.getvalue() if code in (0, 1) else err.getvalue())

    def test_capture_replay_original_provenance_and_conflicts(self):
        args = (self.bundle, self.source, 'new', 'tool/1', 'synthetic', AT)
        result = capture(*args, request_id='capture-1')
        before = self.snapshot()
        self.assertEqual(capture(*args[:-1], '2099-01-01T00:00:00Z', request_id='capture-1'), result)
        self.assertEqual(before, self.snapshot())
        self.error('request_conflict', lambda: capture(self.bundle, self.source, 'new', 'other/1', 'synthetic', AT, 'capture-1'))
        self.source.write_bytes(b'changed bytes')
        self.error('request_conflict', lambda: capture(*args, request_id='capture-1'))
        self.assertEqual(before, self.snapshot())

    def test_curate_replays_before_stale_cas_and_after_unrelated_advances(self):
        first = self.curate('curate-1', 'absent')
        self.assertEqual(first, 'concepts/rules/r000001.md')
        self.assertEqual(self.curate(), 'concepts/rules/r000002.md')
        before = self.snapshot()
        self.assertEqual(self.curate('curate-1', 'absent', now='2099-01-01T00:00:00Z'), first)
        self.assertEqual(before, self.snapshot())
        for changed in ({'actor': 'other/1'}, {'title': 'new'}, {'status': 'stable'},
                        {'kind': 'Other'}, {'stale_after': '2099-01-01T00:00:00Z'},
                        {'expect_current': 'r000002'}, {'sources': ['source', 'source']}):
            args = dict(changed)
            expected = args.pop('expect_current', 'absent')
            self.error('request_conflict', lambda: self.curate('curate-1', expected, **args))
        self.body.write_text('different body same file')
        self.error('request_conflict', lambda: self.curate('curate-1', 'absent'))
        self.assertEqual(before, self.snapshot())

    def test_source_hashes_and_body_bytes_not_paths_define_payload(self):
        first = self.curate('key', 'absent')
        other = self.root / 'same-body'
        other.write_bytes(self.body.read_bytes())
        self.assertEqual(self.curate('key', 'absent', body_file=other), first)
        provenance = self.bundle / 'sources/source/provenance.json'
        provenance.write_bytes(provenance.read_bytes() + b'\n')
        self.error('request_conflict', lambda: self.curate('key', 'absent'))
        provenance.write_bytes(provenance.read_bytes()[:-1])
        raw = self.bundle / 'sources/source/content.raw'
        raw.write_bytes(b'changed')
        self.error('request_conflict', lambda: self.curate('key', 'absent'))

    def test_review_replay_does_not_append_or_move_current(self):
        self.curate()
        first = self.review('review-1')
        self.curate()
        before = self.snapshot()
        self.assertEqual(self.review('review-1'), first)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(first['verified']), 1)
        for changed in ({'actor': 'human:test'}, {'evidence': 'https://example.invalid/evidence'},
                        {'revision': 'r000002'}):
            self.error('request_conflict', lambda: self.review('review-1', **changed))
        (self.bundle / 'sources/source/content.raw').write_bytes(b'new evidence')
        self.error('request_conflict', lambda: self.review('review-1'))

    def test_cas_failures_have_no_receipt_or_knowledge_effect(self):
        self.curate('first', 'absent')
        before = self.snapshot()
        for expected in ('absent', 'r000002'):
            self.error('precondition_failed', lambda: self.curate('stale', expected))
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.curate('next', 'r000001'), 'concepts/rules/r000002.md')
        self.error('precondition_failed', lambda: self.review('stale-review'))
        self.assertFalse((self.bundle / ROOT / 'stale-review').exists())

    def test_ids_pending_corruption_and_effect_integrity(self):
        for key in ('../outside', '/outside', 'UPPER', '', 'x' * 65):
            self.error('invalid_input', lambda: self.curate(key))
        self.curate('good', 'absent')
        folder = self.bundle / ROOT / 'good'
        result = folder / 'result.json'
        original = result.read_bytes()
        for data in (b'{', b'{}', original.replace(b'checksum', b'badcheck')):
            result.write_bytes(data)
            before = self.snapshot()
            self.error('recovery_required', lambda: self.curate('good', 'absent'))
            self.assertEqual(before, self.snapshot())
        result.write_bytes(original)
        result.unlink()
        self.error('recovery_required', lambda: self.curate('good', 'absent'))
        result.write_bytes(original)
        (self.bundle / 'concepts/rules/r000001.md').write_text('changed')
        self.error('recovery_required', lambda: self.curate('good', 'absent'))

    def test_receipt_symlinks_are_not_followed(self):
        outside = self.root / 'outside'
        outside.mkdir()
        receipts = self.bundle / ROOT
        receipts.symlink_to(outside, target_is_directory=True)
        self.error('recovery_required', lambda: self.curate('key', 'absent'))
        self.assertEqual(list(outside.iterdir()), [])
        receipts.unlink()
        self.curate('key', 'absent')
        result = receipts / 'key/result.json'
        result.unlink()
        result.symlink_to(self.source)
        self.error('recovery_required', lambda: self.curate('key', 'absent'))
        self.assertEqual(self.source.read_bytes(), b'synthetic source\r\n\xff')

    def test_receipts_are_not_knowledge_and_reads_preserve_bytes(self):
        self.curate('key', 'absent')
        (self.bundle / ROOT / 'not-a-note.md').write_text('invalid archive')
        before = self.snapshot()
        self.assertEqual(self.cli('check', self.bundle)['invalid'], [])
        self.assertEqual(len(self.cli('search', self.bundle, 'archive')), 1)
        self.assertEqual(self.cli('recall', self.bundle, 'archive')['matched'], 1)
        self.assertEqual(len(self.cli('list', self.bundle)), 1)
        self.assertEqual(before, self.snapshot())

    def test_structured_parser_domain_io_and_check_compatibility(self):
        for args, code in [([], 'arguments'), (['unknown'], 'arguments'),
                           (['curate', self.bundle, 'id'], 'arguments'),
                           (['search', self.bundle, '!!!'], 'invalid_input'),
                           (['show', self.root / 'missing', 'id'], 'not_found'),
                           (['curate', self.bundle, 'id', '--body', self.body, '--source', 'source',
                             '--actor', 'tool/1', '--expect-current', 'bad'], 'invalid_input')]:
            self.assertEqual(self.cli(*args, code=2)['error']['code'], code)
        (self.bundle / 'bad.md').write_text('bad metadata')
        self.assertTrue(self.cli('check', self.bundle, code=1)['invalid'])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(['search', str(self.bundle), '!!!']), 2)
        self.assertEqual(json.loads(err.getvalue()), {'error': 'Query needs at least one word'})
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['search', str(self.bundle), 'archive', '--error-format', 'json'])

    def test_unicode_and_nonfinite_errors_remain_strict_json(self):
        for message in ('보고서 \ud800', 'NaN Infinity ' * 1000):
            with patch('local_knowledge_wiki.cli.search', side_effect=ValueError(message)):
                result = self.cli('search', self.bundle, 'archive', code=2)
                self.assertEqual(result['error']['code'], 'invalid_input')
                self.assertLessEqual(len(encoded(result)), 6500)
        process = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli',
                                  '--error-format=json', 'search', str(self.bundle), '!!!'],
                                 env={**os.environ, 'PYTHONIOENCODING': 'utf-8:strict'},
                                 capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(process.stdout, b'')
        self.assertEqual(json.loads(process.stderr.decode('utf-8'))['error']['code'], 'invalid_input')

    def test_lock_contention_reserves_no_request(self):
        before = self.snapshot()
        with Store(self.bundle) as store, store.lock():
            self.error('locked', lambda: self.curate('key', 'absent'))
            self.assertFalse((self.bundle / ROOT).exists())
        self.assertEqual(before, self.snapshot())

    def test_capture_fault_boundaries_are_not_reexecuted(self):
        original_create = Store.create
        for stage in ('intent.json', 'content.raw', 'provenance.json', 'result.json'):
            with self.subTest(stage=stage):
                key = stage.replace('.', '-')
                source_id = key
                def create(store, path, data):
                    if path.endswith(stage):
                        if stage == 'provenance.json':
                            original_create(store, path, data)
                        raise OSError(errno.EIO, 'injected failure')
                    return original_create(store, path, data)
                with patch.object(Store, 'create', create):
                    self.error('recovery_required', lambda: capture(self.bundle, self.source, source_id,
                               'tool/1', 'synthetic', AT, key))
                before = self.snapshot()
                self.error('recovery_required', lambda: capture(self.bundle, self.source, source_id,
                           'tool/1', 'synthetic', AT, key))
                self.assertEqual(before, self.snapshot())
                folder = self.bundle / 'sources' / source_id
                self.assertEqual(folder.exists(), stage != 'intent.json')
                self.assertEqual((folder / 'content.raw').exists(), stage in ('provenance.json', 'result.json'))
                self.assertEqual((folder / 'provenance.json').exists(), stage in ('provenance.json', 'result.json'))

    def test_revision_and_index_faults_leave_explicit_partial_state(self):
        original_create = Store.create
        for stage in ('revision', 'index', 'result'):
            key = 'fault-' + stage
            def create(store, path, data):
                if stage == 'revision' and path.startswith('concepts/'):
                    raise OSError(errno.EIO, 'injected revision failure')
                if stage == 'result' and path.endswith('/result.json'):
                    raise OSError(errno.EIO, 'injected receipt finalization failure')
                return original_create(store, path, data)
            with patch.object(Store, 'create', create):
                if stage == 'index':
                    with patch.object(Store, 'replace_index', side_effect=OSError(errno.EIO, 'index failure')):
                        self.error('recovery_required', lambda: self.curate(key, 'absent'))
                else:
                    self.error('recovery_required', lambda: self.curate(key, 'absent'))
            before = self.snapshot()
            self.error('recovery_required', lambda: self.curate(key, 'absent'))
            self.assertEqual(before, self.snapshot())
            paths = list((self.bundle / 'concepts/rules').glob('r*.md')) if (self.bundle / 'concepts/rules').exists() else []
            if stage == 'revision':
                self.assertEqual(paths, [])
            elif stage == 'index':
                self.assertEqual(len(paths), 1)
                self.assertNotIn('concepts/rules/', (self.bundle / 'index.md').read_text())
            else:
                self.assertEqual(len(paths), 2)
                self.assertIn('r000002', (self.bundle / 'index.md').read_text())

    def test_completed_receipt_after_failed_sync_can_prove_observed_success(self):
        from local_knowledge_wiki.requests import sync_receipt
        calls = []
        def sync(store, folder):
            calls.append(folder)
            if len(calls) == 2:
                raise OSError(errno.EIO, 'final directory sync failed')
            sync_receipt(store, folder)
        with patch('local_knowledge_wiki.requests.sync_receipt', sync):
            self.error('recovery_required', lambda: self.curate('key', 'absent'))
        before = self.snapshot()
        self.assertEqual(self.curate('key', 'absent'), 'concepts/rules/r000001.md')
        self.assertEqual(before, self.snapshot())

    def test_concurrent_same_key_and_competing_cas_writers(self):
        def command(key, concept):
            return [sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json',
                    'curate', str(self.bundle), concept, '--body', str(self.body), '--source', 'source',
                    '--actor', 'tool/1', '--request-id', key, '--expect-current', 'absent']
        for concept, keys in [('same', ['same-key', 'same-key']), ('cas', ['cas-a', 'cas-b'])]:
            commands = [command(key, concept) for key in keys]
            processes = [subprocess.Popen(c, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for c in commands]
            try:
                results = [p.communicate(timeout=15) for p in processes]
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.kill()
                        p.communicate()
            self.assertGreaterEqual(sum(p.returncode == 0 for p in processes), 1)
            for p, (out, err), args in zip(processes, results, commands):
                if p.returncode:
                    code = json.loads(err)['error']['code']
                    self.assertIn(code, ('locked', 'precondition_failed'))
                    if code == 'locked':
                        retried = subprocess.run(args, capture_output=True, timeout=15)
                        expected = 0 if concept == 'same' else 2
                        self.assertEqual(retried.returncode, expected, retried.stderr)
            self.assertEqual(len(list((self.bundle / 'concepts' / concept).glob('r*.md'))), 1)

    def test_new_request_validation_failures_do_not_reserve_identity(self):
        before = self.snapshot()
        self.error('already_exists', lambda: capture(self.bundle, self.source, 'source', 'tool/1', 'synthetic', AT, 'new'))
        self.body.write_text('---\ntype: Concept\n---\nnot a prepared body')
        self.error('invalid_input', lambda: self.curate('new'))
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.bundle / ROOT).exists())

    def test_request_ids_are_bundle_wide_and_capture_basename_is_payload(self):
        self.curate('shared', 'absent')
        self.error('request_conflict', lambda: capture(self.bundle, self.source, 'new', 'tool/1', 'synthetic', AT, 'shared'))
        capture(self.bundle, self.source, 'new', 'tool/1', 'synthetic', AT, 'cap')
        renamed = self.root / 'different-name'
        renamed.write_bytes(self.source.read_bytes())
        self.error('request_conflict', lambda: capture(self.bundle, renamed, 'new', 'tool/1', 'synthetic', AT, 'cap'))

    def test_request_directory_and_intent_corruption_fail_closed(self):
        self.curate('key', 'absent')
        intent = self.bundle / ROOT / 'key/intent.json'
        intent.write_text('{"version":99}')
        self.error('recovery_required', lambda: self.curate('key', 'absent'))
        folder = self.bundle / ROOT / 'pending-without-intent'
        folder.mkdir()
        self.error('recovery_required', lambda: self.curate('pending-without-intent'))
        alias = self.bundle / ROOT / 'alias'
        alias.symlink_to(self.root)
        self.error('recovery_required', lambda: self.curate('alias'))

    def test_intent_sync_and_source_reservation_failures_leave_no_knowledge_effect(self):
        before = self.snapshot(receipts=False)
        with patch('local_knowledge_wiki.requests.sync_receipt', side_effect=OSError(errno.EIO, 'intent sync failed')):
            self.error('recovery_required', lambda: self.curate('sync', 'absent'))
        self.assertEqual(before, self.snapshot(receipts=False))
        self.error('recovery_required', lambda: self.curate('sync', 'absent'))
        original_mkdir = os.mkdir
        def mkdir(path, *args, **kwargs):
            if path == 'reserved-source':
                raise OSError(errno.EIO, 'source reservation failed')
            return original_mkdir(path, *args, **kwargs)
        with patch('local_knowledge_wiki.storage.os.mkdir', mkdir):
            self.error('recovery_required', lambda: capture(self.bundle, self.source, 'reserved-source',
                       'tool/1', 'synthetic', AT, 'reserve'))
        self.assertEqual(before, self.snapshot(receipts=False))
        self.error('recovery_required', lambda: capture(self.bundle, self.source, 'reserved-source',
                   'tool/1', 'synthetic', AT, 'reserve'))

    def test_structured_codes_for_index_paths_lock_io_and_internal_errors(self):
        index = self.bundle / 'index.md'
        original = index.read_bytes()
        index.write_text('broken')
        self.assertEqual(self.cli('capture', self.bundle, self.source, '--id', 'new', '--actor', 'a/1',
                                 '--resource', 'synthetic', code=2)['error']['code'], 'invalid_index')
        index.write_bytes(original)
        self.curate()
        link = self.bundle / 'unsafe-link'
        link.symlink_to(self.source)
        self.assertEqual(self.cli('search', self.bundle, 'archive', code=2)['error']['code'], 'unsafe_path')
        link.unlink()
        with Store(self.bundle) as store, store.lock():
            self.assertEqual(self.cli('curate', self.bundle, 'rules', '--body', self.body, '--source', 'source',
                                     '--actor', 'a/1', code=2)['error']['code'], 'locked')
        for failure, code in [(OSError(errno.EIO, 'injected'), 'io_error'),
                              (RuntimeError('unexpected'), 'internal_error')]:
            with patch('local_knowledge_wiki.cli.search', side_effect=failure):
                self.assertEqual(self.cli('search', self.bundle, 'archive', code=2)['error']['code'], code)

    def test_concurrent_capture_and_review_same_key_can_be_replayed(self):
        self.curate()
        commands = [
            ['capture', str(self.bundle), str(self.source), '--id', 'new', '--actor', 'a/1',
             '--resource', 'synthetic', '--request-id', 'capture-key'],
            ['review', str(self.bundle), 'rules', '--revision', 'r000001', '--actor', 'process:test',
             '--evidence', 'sources/source/content.raw', '--request-id', 'review-key'],
        ]
        for args in commands:
            command = [sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json', *args]
            processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            try:
                results = [p.communicate(timeout=15) for p in processes]
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.kill()
                        p.communicate()
            successes = [json.loads(out) for p, (out, _) in zip(processes, results) if p.returncode == 0]
            self.assertTrue(successes)
            for p, (_, err) in zip(processes, results):
                if p.returncode:
                    self.assertEqual(json.loads(err)['error']['code'], 'locked')
            before = self.snapshot()
            replay = subprocess.run(command, capture_output=True, timeout=15)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertEqual(json.loads(replay.stdout), successes[0])
            self.assertEqual(before, self.snapshot())
        self.assertEqual(len(list((self.bundle / 'concepts/rules').glob('r*.md'))), 2)

    def test_last_global_error_format_controls_domain_and_parser_errors(self):
        for formats in [('legacy', 'json'), ('json', 'legacy')]:
            for args in (['show', str(self.bundle), 'missing'], ['curate']):
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    try:
                        actual = main(['--error-format', formats[0], '--error-format', formats[1], *args])
                    except SystemExit as exc:
                        actual = exc.code
                self.assertEqual(actual, 2)
                self.assertEqual(out.getvalue(), '')
                if formats[-1] == 'json':
                    self.assertIsInstance(json.loads(err.getvalue())['error'], dict)
                elif args[0] == 'show':
                    self.assertIsInstance(json.loads(err.getvalue())['error'], str)
                else:
                    self.assertIn('usage:', err.getvalue())

    def test_known_missing_reads_and_unavailable_current_index_have_typed_codes(self):
        self.curate()
        for command, args in [('show', ['missing']), ('history', ['missing']),
                              ('show', ['rules', '--revision', 'r000099']),
                              ('diff', ['rules', 'r000001', 'r000099'])]:
            self.assertEqual(self.cli(command, self.bundle, *args, code=2)['error']['code'], 'not_found')
        index = self.bundle / 'index.md'
        index.write_text('broken')
        self.assertEqual(self.cli('show', self.bundle, 'rules', code=2)['error']['code'], 'invalid_index')
        self.assertEqual(self.cli('show', self.bundle, 'rules', '--revision', 'r000001')['current'], None)
        index.unlink()
        self.assertEqual(self.cli('show', self.bundle, 'rules', code=2)['error']['code'], 'invalid_index')

    def test_keyed_review_retains_surrogate_extensions_in_actual_utf8_stdout(self):
        self.curate()
        target = self.bundle / 'concepts/rules/r000001.md'
        text = target.read_text().replace('type: Concept',
             'type: Concept\nverified: {by: "human:synthetic", at: "2026-01-01T00:00:00Z", x-note: "\\uD800"}')
        target.write_text(text)
        command = [sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json', 'review',
                   str(self.bundle), 'rules', '--revision', 'r000001', '--actor', 'process:test',
                   '--evidence', 'sources/source/content.raw', '--request-id', 'review-unicode']
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8:strict'}
        first = subprocess.run(command, capture_output=True, timeout=15, env=env)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout.decode('utf-8'))['verified'][0]['x-note'], '\ud800')
        before = self.snapshot()
        replay = subprocess.run(command, capture_output=True, timeout=15, env=env)
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(first.stdout, replay.stdout)
        self.assertEqual(before, self.snapshot())

    def test_invalid_current_replay_and_json_parser_unicode_do_not_leak_tracebacks(self):
        self.curate('key', 'absent')
        (self.bundle / 'index.md').write_text('broken')
        self.error('invalid_index', lambda: self.curate('key', 'absent'))
        result = self.cli('curate', self.bundle, 'rules', '--status', '\ud800', code=2)
        self.assertEqual(result['error']['code'], 'arguments')

    def test_expected_current_without_key_and_review_fault_are_locked(self):
        self.curate()
        before = self.snapshot()
        self.error('precondition_failed', lambda: self.curate(expected='absent'))
        self.assertEqual(before, self.snapshot())
        original_create = Store.create
        def create(store, path, data):
            if path == 'concepts/rules/r000002.md':
                self.assertTrue((self.bundle / '.lkw.lock').exists())
                original_create(store, path, data)
                raise OSError(errno.EIO, 'revision created but failed before index')
            return original_create(store, path, data)
        with patch.object(Store, 'create', create):
            self.error('recovery_required', lambda: self.review('review-fault'))
        self.assertIn('r000001', (self.bundle / 'index.md').read_text())
        self.assertTrue((self.bundle / 'concepts/rules/r000002.md').exists())
        after = self.snapshot()
        self.error('recovery_required', lambda: self.review('review-fault'))
        self.assertEqual(after, self.snapshot())

    def test_invalid_repeated_error_format_still_reports_json_parser_failure(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
            main(['--error-format', 'json', '--error-format', 'invalid', 'show'])
        self.assertEqual(json.loads(err.getvalue())['error']['code'], 'arguments')

    def test_receipt_version_requires_integer_and_embedded_intent_exact_types(self):
        self.curate('typed', 'absent')
        folder = self.bundle / ROOT / 'typed'
        intent = folder / 'intent.json'
        completed = folder / 'result.json'
        original_intent = intent.read_bytes()
        original_result = completed.read_bytes()
        for value in (True, 1.0, '1', None):
            with self.subTest(version=value):
                record = json.loads(original_intent)
                record['version'] = value
                intent.write_bytes(encoded(record))
                before = self.snapshot()
                self.error('recovery_required', lambda: self.curate('typed', 'absent'))
                self.assertEqual(before, self.snapshot())
        intent.write_bytes(original_intent)
        for value in (True, 1.0):
            record = json.loads(original_result)
            record['intent']['version'] = value
            record.pop('checksum')
            record['checksum'] = digest(encoded(record))
            completed.write_bytes(encoded(record))
            before = self.snapshot()
            self.error('recovery_required', lambda: self.curate('typed', 'absent'))
            self.assertEqual(before, self.snapshot())
        completed.write_bytes(original_result)
        self.assertEqual(self.curate('typed', 'absent'), 'concepts/rules/r000001.md')

    def test_existing_help_abbreviation_and_global_mode_abbreviation(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            main(['--he'])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn('usage:', out.getvalue())
        for flag in ('--error-f=json', '--e=json'):
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                main([flag, 'curate'])
            self.assertEqual(json.loads(err.getvalue())['error']['code'], 'arguments')
