"""Exact frontmatter and no-effect revision serialization regressions."""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

from local_knowledge_wiki.cli import curate, review, write_revision
from local_knowledge_wiki.format import parse, same_metadata, serialize_revision, validate
from local_knowledge_wiki.storage import Store, WikiError, capture, current_index, init


AT = '2026-10-29T00:00:00+00:00'
BREAKS = ('\n', '\r', '\r\n', '\v', '\f', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029')


class MetadataRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'wiki'
        init(self.bundle)
        self.source = self.root / 'input'
        self.source.write_bytes(b'synthetic source')
        capture(self.bundle, self.source, 'source', 'tool/1', 'synthetic', AT)
        self.body = self.root / 'body'
        self.body.write_bytes('보고서 archive\r\n\n---\nbody fence\x85tail'.encode())

    def snapshot(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes()
                for p in self.bundle.rglob('*') if p.is_file()}

    def curate(self, key=None, **changes):
        args = dict(root=self.bundle, concept_id='rules', body_file=self.body,
                    sources=['source'], actor='tool/1', now=AT, kind='Concept', title='보고서 rules',
                    status='draft', stale_after=None, request_id=key)
        args.update(changes)
        return curate(**args)

    def test_original_multiline_title_rejected_by_real_subprocess_without_effects(self):
        for key in (None, 'bad-title'):
            before = self.snapshot()
            args = [sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json',
                    'curate', str(self.bundle), 'rules', '--body', str(self.body), '--source', 'source',
                    '--actor', 'tool/1', '--title', 'a\n---\nb']
            if key:
                args += ['--request-id', key]
            result = subprocess.run(args, capture_output=True, timeout=10,
                                    env={**os.environ, 'PYTHONIOENCODING': 'utf-8:strict'})
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(json.loads(result.stderr)['error']['code'], 'invalid_input')
            self.assertEqual(before, self.snapshot())
            self.assertFalse((self.bundle / '.lkw-requests').exists())

    def test_imported_indented_separators_multiline_metadata_and_body_fences(self):
        for newline in ('\n', '\r\n'):
            for scalar in ('description: |\n  alpha\n  ---\n  beta\n',
                           "description: 'alpha\n\n  ---\n\n  beta'\n"):
                document = ('---\ntype: Concept\n' + scalar + '---\n---\nbody fence\n').replace('\n', newline)
                meta, body = parse(document)
                self.assertEqual(validate(meta), [])
                self.assertIn('---', meta['description'])
                self.assertEqual(body, '---' + newline + 'body fence' + newline)

    def test_only_exact_lf_or_crlf_delimiters(self):
        for delimiter in (' ---', '\t---', '--- ', '---\t', '---\r\r', '---\x85', '---\u2028', '---\u2029'):
            with self.subTest(delimiter=delimiter), self.assertRaises(WikiError):
                parse(delimiter + '\ntype: Concept\n---\nbody')
        for separator in ('\r', '\x85', '\u2028', '\u2029'):
            with self.subTest(separator=separator), self.assertRaises(WikiError):
                parse('---' + separator + 'type: Concept' + separator + '---' + separator + 'body')
        for ending in (' ---', '--- ', '---\t', '---\r', '---\x85', '---\u2028'):
            with self.subTest(ending=ending), self.assertRaises(WikiError):
                parse('---\ntype: Concept\n' + ending)
        self.assertEqual(parse('---\ntype: Concept\n---')[1], '')

    def test_direct_writer_fields_reject_every_splitline_character_without_effects(self):
        for key in (None, 'bad-input'):
            for linebreak in BREAKS:
                for field in ('title', 'kind', 'actor'):
                    before = self.snapshot()
                    with self.subTest(key=key, linebreak=linebreak, field=field):
                        with self.assertRaises(WikiError) as caught:
                            self.curate(key, **{field: 'a' + linebreak + 'b'})
                        self.assertEqual(caught.exception.code, 'invalid_input')
                        self.assertEqual(before, self.snapshot())
                before = self.snapshot()
                with self.assertRaises(WikiError):
                    capture(self.bundle, self.source, 'new', 'a' + linebreak + 'b', 'synthetic', AT, key)
                self.assertEqual(before, self.snapshot())
        self.assertFalse((self.bundle / '.lkw-requests').exists())

    def test_serialize_corruption_rejected_before_curate_effects_or_intent(self):
        real_dump = yaml.dump
        for key in (None, 'bad-serialization'):
            for corruption in ('invalid', 'metadata', 'body'):
                def corrupt(meta, **kwargs):
                    original = real_dump(meta, **kwargs)
                    if corruption == 'invalid':
                        return 'type: [\n'
                    if corruption == 'metadata':
                        return original.replace('draft', 'stable')
                    return original + '---\ninserted body\n'
                before = self.snapshot()
                with patch('local_knowledge_wiki.format.yaml.dump', corrupt), self.assertRaises(WikiError) as caught:
                    self.curate(key)
                self.assertEqual(caught.exception.code, 'invalid_input')
                self.assertEqual(before, self.snapshot())
                self.assertFalse((self.bundle / '.lkw-requests').exists())

    def test_review_corruption_is_rejected_before_intent(self):
        self.curate()
        real_dump = yaml.dump
        def corrupt(meta, **kwargs):
            return real_dump(meta, **kwargs).replace('status: draft', 'status: stable')
        for key in (None, 'bad-review'):
            before = self.snapshot()
            with patch('local_knowledge_wiki.format.yaml.dump', corrupt), self.assertRaises(WikiError) as caught:
                review(self.bundle, 'rules', 'r000001', 'process:test', 'sources/source/content.raw', key)
            self.assertEqual(caught.exception.code, 'invalid_input')
            self.assertEqual(before, self.snapshot())
            self.assertFalse((self.bundle / '.lkw-requests').exists())

    def test_valid_imported_types_and_aliases_survive_review_with_exact_body(self):
        self.curate()
        target = self.bundle / 'concepts/rules/r000001.md'
        original, body = parse(target.read_bytes().decode())
        shared = ['retained', {'number': float('nan')}]
        original.update({'description': 'alpha\n---\nbeta\n', 'title': 'old\n---\ntitle',
                         'type': 'old\n---\ntype', 'shared-a': shared, 'shared-b': shared,
                         date(2026, 1, 1): {'when': datetime(2026, 1, 2, tzinfo=timezone.utc),
                                           'bytes': b'\x00\xff', 'set': {'가', 'b'}, 'inf': float('inf')}})
        target.write_bytes(('---\n' + yaml.safe_dump(original, allow_unicode=True, sort_keys=False) + '---\n' + body).encode())
        for key in (None, 'imported-review'):
            # The original indexed target is restored only inside this synthetic fixture.
            index = self.bundle / 'index.md'
            index.write_text(index.read_text().replace('r000002', 'r000001'))
            result = review(self.bundle, 'rules', 'r000001', 'process:test', 'sources/source/content.raw', key)
            stored, actual_body = parse((self.bundle / result['revision']).read_bytes().decode())
            self.assertEqual(actual_body, body)
            self.assertEqual(stored['description'], original['description'])
            self.assertEqual(stored['title'], original['title'])
            self.assertEqual(stored['type'], original['type'])
            self.assertTrue(math.isnan(stored['shared-a'][1]['number']))
            self.assertIs(stored['shared-a'], stored['shared-b'])
            self.assertEqual(stored[date(2026, 1, 1)], original[date(2026, 1, 1)])

    def test_spaces_korean_and_successful_request_replays_remain_valid(self):
        first = self.curate('good', actor='도구 버전 1', kind='문서 Concept', title='보고서 rules')
        before = self.snapshot()
        self.assertEqual(self.curate('good', actor='도구 버전 1', kind='문서 Concept', title='보고서 rules'), first)
        self.assertEqual(before, self.snapshot())
        stored, body = parse((self.bundle / first).read_bytes().decode())
        self.assertEqual(body.encode(), self.body.read_bytes())
        self.assertEqual(stored['generated']['by'], '도구 버전 1')
        capture(self.bundle, self.source, 'space-actor', '도구 버전 1', 'synthetic', AT)

    def test_direct_revision_guard_rejects_changed_scalar_types_before_index_mutation(self):
        real_dump = yaml.dump
        for value, serialized in ((True, '1'), (float('nan'), '2.0')):
            meta = {'type': 'Concept', 'custom': value}
            def corrupt(metadata, **kwargs):
                return real_dump(metadata, **kwargs).replace(
                    'custom: true' if value is True else 'custom: .nan', 'custom: ' + serialized)
            before_files = self.snapshot()
            with Store(self.bundle) as store, store.lock():
                before = store.read('index.md')
                index = before.decode()
                entries, start, end = current_index(index)
                with patch('local_knowledge_wiki.format.yaml.dump', corrupt), self.assertRaises(WikiError):
                    write_revision(store, 'rules', meta, 'body', before, index, entries, start, end)
                self.assertEqual(entries, {})
            self.assertEqual(before_files, self.snapshot())

    def test_prepared_bytes_are_rechecked_before_revision_creation(self):
        before_files = self.snapshot()
        with Store(self.bundle) as store, store.lock():
            before = store.read('index.md')
            index = before.decode()
            entries, start, end = current_index(index)
            with self.assertRaises(WikiError):
                write_revision(store, 'rules', {'type': 'Concept'}, 'expected body', before,
                               index, entries, start, end, b'---\ntype: Concept\n---\nchanged body')
            self.assertEqual(entries, {})
        self.assertEqual(before_files, self.snapshot())

    def test_imported_nel_survives_keyed_and_unkeyed_real_review(self):
        for key in (None, 'nel-review'):
            concept = 'unkeyed-nel' if key is None else 'keyed-nel'
            path = self.curate(concept_id=concept)
            target = self.bundle / path
            original = ('---\ntype: Concept\ntitle: 보고서\nstatus: draft\n'
                        'description: "한글 a\\Nb"\ncustom: {"key\\Npart": "값\\Npart"}\n'
                        '---\n' + self.body.read_bytes().decode()).encode()
            target.write_bytes(original)
            original_meta, original_body = parse(original.decode())
            self.assertEqual(original_meta['description'], '한글 a\x85b')
            command = [sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json',
                       'review', str(self.bundle), concept, '--revision', 'r000001',
                       '--actor', 'process:test', '--evidence', 'sources/source/content.raw']
            if key:
                command += ['--request-id', key]
            before = self.snapshot()
            result = subprocess.run(command, capture_output=True, timeout=10,
                                    env={**os.environ, 'PYTHONIOENCODING': 'utf-8:strict'})
            if result.returncode:
                self.assertEqual(before, self.snapshot())
                self.assertFalse((self.bundle / '.lkw-requests' / str(key)).exists())
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            stored_bytes = (self.bundle / json.loads(result.stdout)['revision']).read_bytes()
            stored, body = parse(stored_bytes.decode())
            stored.pop('verified')
            self.assertTrue(same_metadata(original_meta, stored))
            self.assertEqual(body, original_body)
            self.assertEqual(target.read_bytes(), original)
            self.assertIn('한글'.encode(), stored_bytes)
            self.assertIn(b'\\N', stored_bytes)
            for name, data in before.items():
                if name != 'index.md':
                    self.assertEqual(self.snapshot()[name], data)
            after = self.snapshot()
            replay = subprocess.run(command, capture_output=True, timeout=10)
            self.assertEqual(replay.returncode, 0 if key else 2, replay.stderr)
            if key:
                self.assertEqual(json.loads(replay.stdout), json.loads(result.stdout))
            else:
                self.assertEqual(json.loads(replay.stderr)['error']['code'], 'precondition_failed')
            self.assertEqual(after, self.snapshot())

    def test_yaml_line_break_values_roundtrip_and_keep_readable_korean(self):
        for separator in BREAKS:
            with self.subTest(separator=separator):
                meta = {'type': 'Concept', 'description': '한글 a' + separator + 'b'}
                data = serialize_revision(meta, '본문\r\n---\n')
                loaded, body = parse(data.decode())
                self.assertTrue(same_metadata(meta, loaded))
                self.assertEqual(body, '본문\r\n---\n')
                self.assertIn('한글'.encode(), data)
