"""Synthetic immutable context, replay, admission and whole-report boundaries."""

import contextlib
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from local_knowledge_wiki import annotations
from local_knowledge_wiki.cli import annotate, curate, main, review
from local_knowledge_wiki.context import context
from local_knowledge_wiki.errors import WikiError
from local_knowledge_wiki.format import parse, same_metadata, serialize_revision
from local_knowledge_wiki.inspection import inspect_storage
from local_knowledge_wiki.recall import render
from local_knowledge_wiki.requests import digest, encoded
from local_knowledge_wiki.storage import END, START, Store, capture, init, render_entries


AT = '2026-11-01T12:00:00+00:00'
LATER = '2026-11-02T12:00:00+00:00'


def data(text='Ran synthetic checks'):
    return {'work_id': 'task', 'recipients': ['all'],
            'completed': [{'id': 'tests', 'text': text, 'evidence': [{'resource': '/sources/source/content.raw'}]}],
            'decisions': [], 'open_questions': [], 'lessons': [
                {'id': 'lesson', 'text': 'Test the boundary', 'evidence': [], 'review': {'status': 'proposed'}}]}


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        init(self.bundle)
        self.source = self.root / 'source'
        self.source.write_bytes(b'synthetic evidence')
        capture(self.bundle, self.source, 'source', 'test/1', 'synthetic', AT)
        self.body = self.root / 'body'
        self.body.write_bytes('Exact body\r\n결정\n'.encode())
        self.file = self.root / 'context.json'
        self.write(data())

    def write(self, value):
        self.file.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def curate(self, name='work', key=None, annotations_file=None, expected=None):
        return curate(self.bundle, name, self.body, ['source'], 'test/1', AT, 'WorkContext',
                      name, 'draft', None, key, expected, annotations_file)

    def annotate(self, revision='r000001', key=None, now=AT):
        return annotate(self.bundle, 'work', revision, 'context', self.file, 'process:test', now, key)

    def snapshot(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*') if p.is_file()}

    def error(self, code, fn):
        with self.assertRaises(WikiError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)

    def test_legacy_omission_has_exact_payload_and_no_metadata_extension(self):
        path = self.curate(key='old', expected='absent')
        source = self.bundle / 'sources/source'
        payload = {'id': 'work', 'body_sha256': digest(self.body.read_bytes()),
                   'sources': [['source', digest((source / 'content.raw').read_bytes()),
                                digest((source / 'provenance.json').read_bytes())]],
                   'actor': 'test/1', 'type': 'WorkContext', 'title': 'work', 'status': 'draft',
                   'stale_after': None, 'expect_current': 'absent'}
        intent = encoded({'version': 1, 'command': 'curate',
                          'fingerprint': digest(encoded({'command': 'curate', 'payload': payload}))})
        self.assertEqual((self.bundle / '.lkw-requests/old/intent.json').read_bytes(), intent)
        self.assertNotIn(annotations.KEY, parse((self.bundle / path).read_text())[0])
        before = self.snapshot()
        self.assertEqual(self.curate(key='old', expected='absent', annotations_file=None), path)
        self.assertEqual(before, self.snapshot())

    def test_curate_annotations_exact_bytes_and_renamed_input_replay(self):
        self.write({'version': 1, 'context': data()})
        path = self.curate(key='create', annotations_file=self.file, expected='absent')
        meta, body = parse((self.bundle / path).read_bytes().decode())
        self.assertEqual(body.encode(), self.body.read_bytes())
        self.assertEqual(meta[annotations.KEY]['context']['recorded_at'], AT)
        self.assertNotIn('verified', meta)
        renamed = self.root / 'renamed'
        renamed.write_bytes(self.file.read_bytes())
        before = self.snapshot()
        self.assertEqual(self.curate(key='create', annotations_file=renamed, expected='absent'), path)
        self.assertEqual(before, self.snapshot())
        renamed.write_bytes(renamed.read_bytes() + b' ')
        self.error('request_conflict', lambda: self.curate(key='create', annotations_file=renamed, expected='absent'))
        self.assertEqual(before, self.snapshot())

    def test_annotate_preserves_imported_values_and_body_but_clears_only_new_verified(self):
        self.curate()
        reviewed = review(self.bundle, 'work', 'r000001', 'human:test', 'sources/source/content.raw', now=AT)
        target = self.bundle / reviewed['revision']
        meta, body = parse(target.read_bytes().decode())
        shared = [date(2026, 1, 1), float('nan')]
        meta.update({'unknown': {date(2026, 1, 1): shared}, 'shared-a': shared, 'shared-b': shared})
        meta[annotations.KEY] = {'version': 1, 'future': {'uninterpreted': [1, True, None]}}
        target.write_bytes(serialize_revision(meta, body))
        original = target.read_bytes()
        result = self.annotate('r000002', 'annotation')
        after, actual_body = parse((self.bundle / result['revision']).read_bytes().decode())
        self.assertEqual(body, actual_body)
        expected = {k: v for k, v in meta.items() if k not in (annotations.KEY, 'verified')}
        actual = {k: v for k, v in after.items() if k != annotations.KEY}
        self.assertTrue(same_metadata(expected, actual))
        self.assertIs(after['shared-a'], after['shared-b'])
        self.assertEqual(after[annotations.KEY]['future'], meta[annotations.KEY]['future'])
        self.assertEqual(target.read_bytes(), original)
        self.assertIn('verified', parse(original.decode())[0])
        self.assertNotIn('verified', after)
        self.assertEqual(inspect_storage(self.bundle)['receipts']['states'], {'self_consistent': 1})

    def test_replay_precedes_cas_and_implicit_time_is_not_identity(self):
        self.curate()
        first = self.annotate(key='implicit', now=None)
        self.curate()
        renamed = self.root / 'copy'
        renamed.write_bytes(self.file.read_bytes())
        before = self.snapshot()
        result = annotate(self.bundle, 'work', 'r000001', 'context', renamed, 'process:test', request_id='implicit')
        self.assertEqual(result, first)
        self.assertEqual(before, self.snapshot())
        self.error('request_conflict', lambda: self.annotate(key='implicit', now=AT))
        self.write(data('Changed declaration'))
        self.error('request_conflict', lambda: self.annotate(key='implicit', now=None))
        self.assertEqual(before, self.snapshot())
        self.error('precondition_failed', lambda: self.annotate(key='stale'))
        self.assertEqual(before, self.snapshot())

    def test_explicit_equivalent_times_and_precision_actor_validation_before_lock(self):
        self.curate()
        first = self.annotate(key='clock', now='2026-11-01T21:00:00+09:00')
        before = self.snapshot()
        self.assertEqual(self.annotate(key='clock', now='2026-11-01T12:00:00Z'), first)
        self.error('request_conflict', lambda: self.annotate(key='clock', now=LATER))
        self.assertEqual(before, self.snapshot())
        for actor, at in [('bad', AT), ('human:a\n', AT), ('test/1', '2026-11-01T12:00:00.0000000Z'),
                          ('test/1', '2026-11-01T12:00:00')]:
            with self.subTest(actor=actor, at=at), patch.object(Store, 'lock', side_effect=AssertionError('locked')):
                self.error('invalid_input', lambda: annotate(self.bundle, 'work', 'r000002', 'context', self.file, actor, at))
        self.assertEqual(before, self.snapshot())

    def test_pending_corrupt_and_invalid_receipt_result_never_reexecute(self):
        self.curate()
        with patch.object(Store, 'stage_index', side_effect=OSError('injected stage failure')):
            self.error('recovery_required', lambda: self.annotate(key='pending'))
        before = self.snapshot()
        self.error('recovery_required', lambda: self.annotate(key='pending'))
        self.assertEqual(before, self.snapshot())
        self.annotate(key='complete')
        result_path = self.bundle / '.lkw-requests/complete/result.json'
        record = json.loads(result_path.read_bytes())
        record['result']['extra'] = 'not allowed'
        record.pop('checksum')
        record['checksum'] = digest(encoded(record))
        result_path.write_bytes(encoded(record))
        before = self.snapshot()
        self.error('recovery_required', lambda: self.annotate(key='complete'))
        self.assertEqual(before, self.snapshot())

    def test_preflight_root_section_index_and_receipt_caps_leave_no_intent(self):
        self.curate()
        before = self.snapshot()
        for target in ('local_knowledge_wiki.annotations.SECTION_BYTES', 'local_knowledge_wiki.annotations.ROOT_BYTES',
                       'local_knowledge_wiki.cli.INDEX_BYTES', 'local_knowledge_wiki.requests.RECEIPT_BYTES'):
            with self.subTest(target=target), patch(target, 1):
                self.error('input_too_large', lambda: self.annotate(key='limit'))
            self.assertEqual(before, self.snapshot())
        self.write({'version': 1, 'context': data()})
        with patch('local_knowledge_wiki.requests.RECEIPT_BYTES', 1):
            self.error('input_too_large', lambda: self.curate('another', 'limit', self.file, 'absent'))
        self.assertEqual(before, self.snapshot())

    def test_input_exact_boundary_plus_one_fifo_symlink_and_strict_json(self):
        self.curate()
        raw = self.file.read_bytes()
        self.file.write_bytes(raw + b' ' * (annotations.INPUT_BYTES - len(raw)))
        self.annotate()
        before = self.snapshot()
        self.file.write_bytes(self.file.read_bytes() + b' ')
        self.error('input_too_large', lambda: self.annotate('r000002', 'overflow'))
        for value in (b'{"work_id":1,"work_id":2}', b'{"value":NaN}', b'\xff', b'[' * 1500):
            self.file.write_bytes(value)
            with self.assertRaises(WikiError):
                self.annotate('r000002', 'bad-json')
        self.file.unlink()
        self.file.symlink_to(self.source)
        with self.assertRaises(OSError):
            self.annotate('r000002', 'symlink')
        self.file.unlink()
        import os
        os.mkfifo(self.file)
        self.error('unsafe_path', lambda: self.annotate('r000002', 'fifo'))
        self.assertEqual(before, self.snapshot())

    def test_bad_context_shapes_review_and_evidence_are_rejected_without_effects(self):
        self.curate()
        before = self.snapshot()
        invalid = []
        value = data(); value['unexpected'] = True; invalid.append(value)
        value = data(); value['recipients'] = ['same', 'same']; invalid.append(value)
        value = data(); value['completed'] *= 2; invalid.append(value)
        value = data(); value['completed'][0]['text'] = '가' * 342; invalid.append(value)
        value = data(); value['lessons'][0]['review'] = {'status': 'accepted'}; invalid.append(value)
        for resource in ('../private', '/a/../private', '/.lkw-requests/key/result.json',
                         '/folder/.git/secret', 'https://user:secret@example.org', 'https://example.org:0',
                         'https://example.org/%zz', '/a?query'):
            value = data(); value['completed'][0]['evidence'] = [{'resource': resource}]; invalid.append(value)
        for value in invalid:
            self.write(value)
            with self.subTest(value=value), self.assertRaises((WikiError, ValueError, TypeError)):
                self.annotate(key='invalid')
            self.assertEqual(before, self.snapshot())

    def test_section_and_owned_tree_exact_caps_depth_cycles_and_legacy_unknowns(self):
        value = annotations.envelope(data(), 'process:test', AT)
        size = len(annotations.json_bytes(value))
        with patch.object(annotations, 'SECTION_BYTES', size):
            self.assertEqual(annotations.envelope(data(), 'process:test', AT), value)
        with patch.object(annotations, 'SECTION_BYTES', size - 1):
            self.error('input_too_large', lambda: annotations.envelope(data(), 'process:test', AT))
        root = {'version': 1, 'context': value, 'future': {'data': [True, 1, None]}}
        size = len(annotations.json_bytes(root))
        with patch.object(annotations, 'ROOT_BYTES', size):
            annotations.stored_root(root)
        with patch.object(annotations, 'ROOT_BYTES', size - 1):
            self.error('input_too_large', lambda: annotations.stored_root(root))
        cyclic = []; cyclic.append(cyclic)
        self.error('invalid_input', lambda: annotations.json_bytes(cyclic))
        self.error('input_too_large', lambda: annotations.json_bytes([[[[[[[[[[]]]]]]]]]]))
        self.error('input_too_large', lambda: annotations.json_bytes([0] * 4096))
        self.curate()
        path = self.bundle / 'concepts/work/r000001.md'
        for root in ({'version': True}, {'version': 2}, {'version': 1, 'context': {}},
                     {'version': 1, 'future': {'bad': date(2026, 1, 1)}}):
            meta, body = parse(path.read_text()); meta[annotations.KEY] = root
            path.write_bytes(serialize_revision(meta, body))
            before = self.snapshot()
            with self.assertRaises(WikiError):
                self.annotate(key='unsupported')
            self.assertEqual(before, self.snapshot())
            output = context(self.bundle, now=AT)
            self.assertTrue(output['partial'])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(['show', str(self.bundle), 'work']), 0)

    def test_context_current_scope_filters_and_declared_lessons_without_source_reads(self):
        self.curate()
        value = data()
        value['recipients'] = ['codex']
        value['lessons'][0]['review'] = {'status': 'accepted', 'by': 'process:reviewer',
                                       'at': '2026-11-01T21:00:00+09:00', 'reason': 'Explicit declaration'}
        self.write(value)
        result = self.annotate()
        private = self.bundle / 'concepts/work/r999999.md'
        private.write_text('private historical note must not be opened')
        (self.bundle / 'concepts/unselected').mkdir()
        (self.bundle / 'concepts/unselected/r000001.md').symlink_to(self.source)
        index = self.bundle / 'index.md'
        index.write_text(START + render_entries({'work': result['revision'],
                           'unselected': 'concepts/unselected/r000001.md'}) + END)
        before = self.snapshot()
        original_read = Store.read
        opened = []
        def read(store, path, *args, **kwargs):
            opened.append(path)
            return original_read(store, path, *args, **kwargs)
        with patch.object(Store, 'read', read):
            output = context(self.bundle, scope=['work', 'work'], recipient='codex', since=AT, now=AT)
        self.assertEqual(set(opened), {'index.md', result['revision']})
        item = output['results'][0]
        self.assertEqual(item['sha256'], digest((self.bundle / result['revision']).read_bytes()))
        self.assertEqual(item['data']['lessons'][0]['review']['at'], AT)
        self.assertEqual(item['data']['lessons'][0]['review']['by'], 'process:reviewer')
        self.assertNotIn('verified', parse((self.bundle / result['revision']).read_text())[0])
        self.assertFalse(output['partial'])
        self.assertEqual(context(self.bundle, scope=['work'], recipient='claude', now=AT)['matched_total'], 0)
        self.assertEqual(context(self.bundle, scope=['work'], since=LATER, now=AT)['matched_total'], 0)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(context(self.bundle, scope=[], now=AT)['scan']['processed'], 0)
        self.error('not_found', lambda: context(self.bundle, scope=['missing'], now=AT))

    def test_context_scan_byte_reference_diagnostic_caps_and_missing_index(self):
        self.curate(); self.annotate()
        self.curate('second')
        with patch('local_knowledge_wiki.context.NOTE_LIMIT', 1):
            output = context(self.bundle, now=AT)
            self.assertEqual(output['scan']['processed'], 1)
            self.assertFalse(output['scan']['complete'])
            self.assertIsNone(output['matched_total'])
        with patch('local_knowledge_wiki.context.READ_BYTES', 1):
            output = context(self.bundle, now=AT)
            self.assertEqual(output['scan']['budget_charged_bytes'], 1)
            self.assertIsNone(output['scan']['read_bytes'])
            self.assertTrue(output['partial'])
        with patch('local_knowledge_wiki.context.REFERENCE_LIMIT', 0):
            output = context(self.bundle, scope=['work'], now=AT)
            self.assertEqual(output['results'], [])
            self.assertFalse(output['scan']['complete'])
        for path in self.bundle.glob('concepts/*/r00000*.md'):
            path.write_bytes(b'\xff')
        with patch('local_knowledge_wiki.context.DIAGNOSTIC_LIMIT', 1):
            output = context(self.bundle, now=AT)
            self.assertEqual(len(output['diagnostics']), 1)
            self.assertEqual(output['omitted']['diagnostics'], 1)
            self.assertIsNone(output['matched_total'])
        (self.bundle / 'index.md').write_text('broken')
        self.error('invalid_index', lambda: context(self.bundle, now=AT))

    def test_whole_report_bounds_whole_records_unknown_sections_and_index_race(self):
        self.curate(); self.annotate()
        self.curate('a'); self.curate('b')
        for name in ('a', 'b'):
            annotate(self.bundle, name, 'r000001', 'context', self.file, 'test/1', AT)
        for budget in (2048, 3000, 12000):
            result = context(self.bundle, max_chars=budget, now=AT, limit=1)
            self.assertLessEqual(len(render(result)), budget)
            self.assertEqual(result['matched_total'], 3)
            self.assertEqual(result['omitted']['records'], 3 - len(result['results']))
            self.assertTrue(result['partial'])
            for item in result['results']:
                self.assertEqual(len(item['sha256']), 64)
                self.assertEqual(item['data']['completed'][0]['text'], data()['completed'][0]['text'])
        original_read = Store.read
        index_reads = []
        def read(store, path, *args, **kwargs):
            if path == 'index.md':
                index_reads.append(path)
                if len(index_reads) == 2:
                    return b'changed index'
            return original_read(store, path, *args, **kwargs)
        with patch.object(Store, 'read', read):
            result = context(self.bundle, now=AT)
        self.assertTrue(result['index_changed'])
        self.assertFalse(result['scan']['complete'])
        self.assertIsNone(result['matched_total'])
        path = self.bundle / 'concepts/work/r000002.md'
        meta, body = parse(path.read_text()); meta[annotations.KEY]['future'] = {'data': 'not interpreted'}
        path.write_bytes(serialize_revision(meta, body))
        result = context(self.bundle, scope=['work'], now=AT)
        self.assertEqual(result['matched_observed'], 1)
        self.assertTrue(result['partial'])
        self.assertEqual(result['diagnostics'][0]['kind'], 'unsupported_sections')

    def test_context_exact_read_budget_and_missing_lock_do_not_create_artifacts(self):
        self.curate(); result = self.annotate()
        (self.bundle / '.lkw.lock').unlink()
        before = self.snapshot()
        size = len((self.bundle / result['revision']).read_bytes())
        with patch('local_knowledge_wiki.context.READ_BYTES', size):
            output = context(self.bundle, now=AT)
            self.assertTrue(output['scan']['complete'])
            self.assertEqual(output['scan']['read_bytes'], size)
        with patch('local_knowledge_wiki.context.READ_BYTES', size - 1):
            output = context(self.bundle, now=AT)
            self.assertFalse(output['scan']['complete'])
            self.assertIsNone(output['matched_total'])
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.bundle / '.lkw.lock').exists())

    def test_oversized_diagnostics_and_identity_records_fit_minimum_budget(self):
        self.curate(); self.annotate()
        path = self.bundle / 'concepts/work/r000002.md'
        meta, body = parse(path.read_text())
        long = data('가' * 341)
        long['completed'] = [{**long['completed'][0], 'id': f'n{i}'} for i in range(30)]
        meta[annotations.KEY]['context'] = annotations.envelope(long, 'test/1', AT)
        path.write_bytes(serialize_revision(meta, body))
        output = context(self.bundle, max_chars=2048, now=AT)
        self.assertEqual(output['results'], [])
        self.assertEqual(output['omitted']['records'], 1)
        self.assertLessEqual(len(render(output)), 2048)
        with patch('local_knowledge_wiki.context.stored_root', side_effect=WikiError('\ud800' * 2000)):
            output = context(self.bundle, max_chars=2048, now=AT)
        self.assertLessEqual(len(render(output)), 2048)
        render(output).encode('utf-8', errors='strict')
        self.assertTrue(output['partial'])

    def test_annotate_target_hash_binding_and_concurrent_change_do_not_hide_partial_state(self):
        self.curate()
        self.annotate(key='bound')
        receipt = json.loads((self.bundle / '.lkw-requests/bound/intent.json').read_bytes())
        payload = {'id': 'work', 'revision': 'r000001', 'section': 'context',
                   'input_sha256': digest(self.file.read_bytes()),
                   'target_sha256': digest((self.bundle / 'concepts/work/r000001.md').read_bytes()),
                   'actor': 'process:test', 'declared_at': AT}
        self.assertEqual(receipt['fingerprint'], digest(encoded({'command': 'annotate', 'payload': payload})))
        original_read = Store.read
        reads = []
        def read(store, path, *args, **kwargs):
            if path == 'concepts/work/r000002.md':
                reads.append(path)
                if len(reads) == 2:
                    return b'changed during operation'
            return original_read(store, path, *args, **kwargs)
        with patch.object(Store, 'read', read):
            self.error('recovery_required', lambda: self.annotate('r000002', 'concurrent'))
        self.assertFalse((self.bundle / 'concepts/work/r000003.md').exists())
        self.assertTrue((self.bundle / '.lkw-requests/concurrent/intent.json').exists())
        before = self.snapshot()
        self.error('recovery_required', lambda: self.annotate('r000002', 'concurrent'))
        self.assertEqual(before, self.snapshot())

    def test_alias_expansion_is_rejected_before_container_encoding(self):
        original = json.JSONEncoder.iterencode
        for length in (4, 16, 64):
            for copies in (2, 8, 24):
                shared = 'x' * length
                value = {'version': 1, 'future': {'seed': shared, 'copies': [shared] * copies}}
                expected = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
                def guard(encoder, item, *args, **kwargs):
                    if item is value:
                        raise AssertionError('Oversized alias tree reached container encoding')
                    return original(encoder, item, *args, **kwargs)
                with self.subTest(length=length, copies=copies):
                    with patch.object(annotations, 'ROOT_BYTES', len(expected)):
                        self.assertEqual(annotations.json_bytes(value), expected)
                    with patch.object(annotations, 'ROOT_BYTES', len(expected) - 1), \
                            patch.object(json.JSONEncoder, 'iterencode', guard):
                        self.error('input_too_large', lambda: annotations.stored_root(value))

    def test_json_encoding_exact_escaped_utf8_bytes_and_shared_container_identity(self):
        values = [''.join(chr(n) for n in range(128)), chr(0x10ffff), 'plain', '가😀', 'quote" and slash\\', '\b\f\n\r\t\x00\x1f', '\u2028\u0085']
        for value in values:
            shared = {'key': value, 'scalars': [None, True, False, -123, 1.25]}
            tree = [shared, shared]
            expected = json.dumps(tree, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
            with self.subTest(value=value):
                with patch.object(annotations, 'ROOT_BYTES', len(expected)):
                    self.assertEqual(annotations.json_bytes(tree), expected)
                with patch.object(annotations, 'ROOT_BYTES', len(expected) - 1):
                    self.error('input_too_large', lambda: annotations.json_bytes(tree))
                self.assertIs(tree[0], tree[1])
        for invalid in (float('inf'), float('nan'), '\ud800', {1: 'non-string key'}, {'date': date(2026, 1, 1)}):
            with self.subTest(invalid=invalid):
                self.error('invalid_input', lambda: annotations.json_bytes(invalid))

    def test_author_section_rejects_escaped_overflow_before_envelope_encoding(self):
        self.write({'version': 1, 'context': data('가\x00"\\' * 4)})
        section = annotations.envelope(data('가\x00"\\' * 4), 'test/1', AT)
        size = len(json.dumps(section, ensure_ascii=False, separators=(',', ':')).encode())
        before = self.snapshot()
        original = json.JSONEncoder.iterencode
        def guard(encoder, item, *args, **kwargs):
            if isinstance(item, dict) and 'recorded_by' in item:
                raise AssertionError('Oversized section reached container encoding')
            return original(encoder, item, *args, **kwargs)
        with patch.object(annotations, 'SECTION_BYTES', size - 1), \
                patch.object(json.JSONEncoder, 'iterencode', guard):
            self.error('input_too_large', lambda: self.curate('oversized', 'no-intent', self.file, 'absent'))
        self.assertEqual(before, self.snapshot())
        with patch.object(annotations, 'SECTION_BYTES', size):
            self.curate('exact', 'exact-input', self.file, 'absent')
        self.curate('plain')
        self.write(data('가\x00"\\' * 4))
        before = self.snapshot()
        with patch.object(annotations, 'SECTION_BYTES', size - 1), \
                patch.object(json.JSONEncoder, 'iterencode', guard):
            self.error('input_too_large', lambda: annotate(self.bundle, 'plain', 'r000001', 'context',
                                                         self.file, 'test/1', AT, 'annotate-no-intent'))
        self.assertEqual(before, self.snapshot())

    def test_imported_alias_context_and_annotate_reject_before_expansion_without_effects(self):
        self.curate()
        path = self.bundle / 'concepts/work/r000001.md'
        shared = '가\x01' * 16
        raw = ('---\ntype: Concept\nx-second-brain-annotations:\n  version: 1\n  future:\n'
               '    seed: &seed ' + json.dumps(shared, ensure_ascii=False) + '\n    copies: ['
               + ', '.join(['*seed'] * 24) + ']\n---\nExact imported body\n')
        path.write_text(raw, encoding='utf-8')
        meta, _ = parse(raw)
        future = meta[annotations.KEY]['future']
        self.assertIs(future['seed'], future['copies'][0])
        before = self.snapshot()
        original = json.JSONEncoder.iterencode
        def guard(encoder, item, *args, **kwargs):
            if isinstance(item, dict) and item.get('version') == 1 and 'future' in item:
                raise AssertionError('Oversized imported aliases reached container encoding')
            return original(encoder, item, *args, **kwargs)
        with patch.object(annotations, 'ROOT_BYTES', 1024), \
                patch.object(json.JSONEncoder, 'iterencode', guard):
            output = context(self.bundle, now=AT)
            self.assertTrue(output['partial'])
            self.assertEqual(output['diagnostics'][0]['code'], 'input_too_large')
            self.error('input_too_large', lambda: self.annotate(key='alias-no-intent'))
        self.assertEqual(before, self.snapshot())

    def test_new_cli_errors_and_no_other_sections(self):
        self.curate()
        for args in (['annotate', str(self.bundle), 'work', '--revision', 'r000001', '--section', 'relations',
                      '--file', str(self.file), '--actor', 'test/1'],
                     ['context', str(self.bundle), '--limit', '0'],
                     ['context', str(self.bundle), '--now', '2026-11-01T12:00:00.0000000Z'],
                     ['context', str(self.bundle), '--max-chars', '100']):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                try:
                    code = main(['--error-format', 'json', *args])
                except SystemExit as exc:
                    code = exc.code
            self.assertEqual(code, 2)
            self.assertIsInstance(json.loads(err.getvalue())['error'], dict)
        with patch('local_knowledge_wiki.platform.sys.platform', 'win32'), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['context', str(self.bundle)]), 2)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(['annotate', '--help'])
        self.assertEqual(caught.exception.code, 0)


if __name__ == '__main__':
    unittest.main()
