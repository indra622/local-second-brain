"""Synthetic health declarations, single-pass scope and explicit source IO."""

import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import test_graph as graph_fixtures
from test_graph import relation
from local_knowledge_wiki import annotations
from local_knowledge_wiki.cli import annotate, main
from local_knowledge_wiki.context import context
from local_knowledge_wiki.graph import graph
from local_knowledge_wiki.health import health
from local_knowledge_wiki.format import parse, serialize_revision, validate
from local_knowledge_wiki.recall import render
from local_knowledge_wiki.storage import Store, capture

AT = '2026-11-02T12:00:00Z'


class HealthTests(unittest.TestCase):
    setUp = graph_fixtures.GraphTests.setUp
    note = graph_fixtures.GraphTests.note
    snapshot = graph_fixtures.GraphTests.snapshot
    error = graph_fixtures.GraphTests.error

    def update(self, section, data, revision='r000001', key=None):
        self.file.write_text(json.dumps(data))
        return annotate(self.bundle, 'a', revision, section, self.file, 'process:test', AT, key)

    def view(self, **kwargs):
        return health(self.bundle, now=AT, max_chars=1000000, **kwargs)

    def test_observation_age_pointer_due_and_note_deadline_are_distinct(self):
        self.note('a')
        self.update('freshness', {'form': 'observation', 'observed_at': '2000-01-01T00:00:00Z', 'evidence': []}, key='observed')
        first = self.view()
        self.assertNotIn('pointer_due', [f['kind'] for f in first['findings']])
        self.assertFalse(first['partial'])
        self.update('freshness', {'form': 'pointer', 'target': {'resource': 'https://example.invalid/current'},
                    'recheck_after': AT, 'evidence': []}, 'r000002', 'pointer')
        before = self.snapshot()
        self.assertEqual(self.update('freshness', {'form': 'pointer', 'target': {'resource': 'https://example.invalid/current'},
                    'recheck_after': AT, 'evidence': []}, 'r000002', 'pointer')['revision'], 'concepts/a/r000003.md')
        self.assertEqual(before, self.snapshot())
        p = self.bundle / 'concepts/a/r000003.md'
        meta, body = parse(p.read_text()); meta['stale_after'] = AT
        p.write_bytes(serialize_revision(meta, body))
        result = self.view()
        kinds = {f['kind'] for f in result['findings']}
        self.assertTrue({'pointer_due', 'pointer_unobserved', 'note_due'} <= kinds)
        self.assertFalse(result['partial'])

    def test_cli_legacy_deadline_values_and_context_relevance_preserve_bundle(self):
        self.note('a', ctx=True)
        p = self.bundle / 'concepts/a/r000001.md'
        original = p.read_text()
        for value in ('"2026-11-01T12:00:00.1234567Z"', '2026-11-01T12:00:00Z'):
            p.write_text(original.replace('type: Concept', 'type: Concept\nstale_after: ' + value))
            before = self.snapshot()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(['health', str(self.bundle), '--now', AT]), 0)
            result = json.loads(out.getvalue())
            self.assertIn('note_due', [f['kind'] for f in result['findings']])
            self.assertFalse(result['partial'])
            self.assertEqual(before, self.snapshot())
        meta, body = parse(original)
        meta[annotations.KEY]['freshness'] = annotations.envelope({'form': 'reference', 'evidence': []}, 'test/1', AT, 'freshness')
        meta[annotations.KEY]['context']['data']['recipients'] = []
        p.write_bytes(serialize_revision(meta, body))
        before = self.snapshot(); out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['health', str(self.bundle), '--now', AT]), 0)
        result = json.loads(out.getvalue())
        self.assertFalse(result['analysis_complete'])
        self.assertTrue(result['partial'])
        self.assertTrue(next(d for d in result['diagnostics'] if d['kind'] == 'invalid_context')['affects_analysis'])
        self.assertEqual(before, self.snapshot())

    def test_cli_legacy_minyear_offset_deadline_preserves_valid_value_and_bytes(self):
        self.note('a')
        target = self.bundle / 'concepts/a/r000001.md'
        value = '0001-01-01T00:00:00+01:00'
        target.write_text("---\ntype: Concept\nstale_after: '" + value + "'\n---\nSynthetic body\n")
        self.assertEqual(validate(parse(target.read_text())[0]), [])
        before = self.snapshot()
        child = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json',
                                'health', str(self.bundle), '--now', '2026-11-02T00:00:00Z'],
                               env={**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')},
                               capture_output=True, timeout=15)
        self.assertEqual(child.returncode, 0, child.stderr)
        result = json.loads(child.stdout)
        due = next(item for item in result['findings'] if item['kind'] == 'note_due')
        self.assertEqual(due['observed'], value)
        self.assertFalse(result['partial'])
        self.assertEqual(before, self.snapshot())

    def test_future_source_classification_and_unlinked_imported_assessments(self):
        self.note('a')
        item = {'resource': '/sources/source/content.raw', 'provenance_basis': 'derived',
                'retained_scope': 'locator_only', 'rationale': 'Declared only', 'evidence': []}
        self.update('source_evidence', {'items': [item]})
        self.update('freshness', {'form': 'observation', 'observed_at': '2099-01-01T00:00:00Z', 'evidence': []}, 'r000002')
        result = self.view()
        self.assertIn('future_observation', [f['kind'] for f in result['findings']])
        self.assertIn('limited_declared_evidence', [f['kind'] for f in result['findings']])
        p = self.bundle / 'concepts/a/r000003.md'; meta, body = parse(p.read_text())
        items = meta[annotations.KEY]['source_evidence']['data']['items']
        items.append({**item, 'provenance_basis': 'primary_record'})
        items.append({**item, 'resource': '/sources/unlinked/content.raw'})
        p.write_bytes(serialize_revision(meta, body))
        kinds = {f['kind'] for f in self.view()['findings']}
        self.assertTrue({'unlinked_assessment', 'assessment_disagreement'} <= kinds)

    def test_invalid_new_sections_no_intent_or_effect_and_section_local_views(self):
        self.note('a', [relation('b')], ctx=True); self.note('b')
        before = self.snapshot()
        for name, value in [('freshness', {'form': 'observation', 'evidence': []}),
                            ('freshness', {'form': 'pointer', 'target': {'resource': '../outside'}, 'evidence': []}),
                            ('freshness', {'form': 'observation', 'observed_at': '2000-01-01T00:00:00.1234567Z', 'evidence': []}),
                            ('source_evidence', {'items': [{'resource': '/sources/absent/content.raw', 'provenance_basis': 'unknown',
                              'retained_scope': 'unknown', 'rationale': 'none', 'evidence': []}]})]:
            self.error('invalid_input', lambda: self.update(name, value, key='invalid'))
            self.assertEqual(before, self.snapshot())
        p = self.bundle / 'concepts/a/r000001.md'; meta, body = parse(p.read_text())
        meta[annotations.KEY]['freshness'] = {'recorded_by': 'test/1', 'recorded_at': AT, 'data': {'form': 'bad'}}
        p.write_bytes(serialize_revision(meta, body))
        self.assertEqual(context(self.bundle, scope=['a'], now=AT)['matched_total'], 1)
        self.assertEqual(graph(self.bundle, path=['a', 'b'], max_chars=1000000)['path_state'], 'found')
        result = self.view()
        self.assertTrue(result['partial'])
        self.assertIn('invalid_section', [f['kind'] for f in result['findings']])

    def test_one_note_pass_default_no_sources_and_structural_distinctions(self):
        self.note('a', [relation('wanted', expectation='wanted'), relation('missing', ident='missing')])
        self.note('b')
        before = self.snapshot(); reads = []; original = Store.read
        def read(store, path, *args, **kwargs):
            reads.append(path)
            return original(store, path, *args, **kwargs)
        with patch.object(Store, 'read', read):
            result = self.view(scope=['a'])
        self.assertEqual(reads, ['index.md', 'concepts/a/r000001.md', 'index.md'])
        self.assertTrue({'wanted_not_indexed', 'not_indexed', 'unchecked_resource'} <= {f['kind'] for f in result['findings']})
        self.assertFalse(result['partial'])
        self.assertEqual(before, self.snapshot())

    def test_legacy_capture_actors_locators_hash_and_bytes_checks(self):
        self.note('a')
        capture(self.bundle, self.source, 'legacy', 'generic old actor', 'opaque\nlocator', '2000-01-01T00:00:00.1234567Z')
        result = self.view(verify_source=['legacy'])
        self.assertEqual(result['verification'][0]['state'], 'matched')
        self.assertNotIn('locator', render(result))
        content = self.bundle / 'sources/legacy/content.raw'; content.write_bytes(b'changed')
        result = self.view(verify_source=['legacy'])
        self.assertEqual(result['verification'][0]['state'], 'hash_mismatch')
        self.assertFalse(result['partial'])
        sidecar = self.bundle / 'sources/legacy/provenance.json'
        original = sidecar.read_bytes()
        for change in ('duplicate', 'bool', 'wrongid', 'nan', 'digest'):
            value = json.loads(original)
            if change == 'bool': value['bytes'] = True
            if change == 'wrongid': value['id'] = 'wrong'
            if change == 'nan': value['resource'] = float('nan')
            if change == 'digest': value['sha256'] = 'bad'
            raw = json.dumps(value).encode() if change != 'duplicate' else original.replace(b'"id":', b'"id":"other","id":')
            sidecar.write_bytes(raw)
            result = self.view(verify_source=['legacy'])
            self.assertEqual(result['verification'][0]['state'], 'invalid_provenance')
            self.assertTrue(result['partial'])

    def test_verification_total_budget_includes_sidecar_and_no_raw_leak(self):
        self.note('a')
        source = self.bundle / 'sources/source'
        size = sum(p.stat().st_size for p in source.iterdir())
        with patch('local_knowledge_wiki.health.VERIFY_BYTES', size):
            result = self.view(verify_source=['source'])
            self.assertEqual(result['verification_io']['bytes_read'], size)
            self.assertEqual(result['verification'][0]['state'], 'matched')
        with patch('local_knowledge_wiki.health.VERIFY_BYTES', size - 1):
            result = self.view(verify_source=['source'])
            self.assertEqual(result['verification'][0]['state'], 'unchecked_budget')
            self.assertLessEqual(result['verification_io']['bytes_read'], size - 1)
        self.assertNotIn('synthetic source', render(result))
        (source / 'content.raw').unlink(); (source / 'content.raw').symlink_to(self.source)
        self.assertEqual(self.view(verify_source=['source'])['verification'][0]['state'], 'unavailable_source_file')

    def test_declared_hash_compare_only_for_explicit_source_and_output_caps(self):
        self.note('a')
        self.update('freshness', {'form': 'reference', 'evidence': [{'resource': '/sources/source/content.raw', 'sha256': '0' * 64}]})
        self.assertNotIn('declared_hash_mismatch', [f['kind'] for f in self.view()['findings']])
        self.assertIn('declared_hash_mismatch', [f['kind'] for f in self.view(verify_source=['source'])['findings']])
        for budget in (2048, 3000, 12000):
            result = health(self.bundle, now=AT, max_chars=budget, verify_source=['source'])
            self.assertLessEqual(len(render(result)), budget)
        with patch('local_knowledge_wiki.graph.NOTE_LIMIT', 0):
            self.assertTrue(self.view()['partial'])
        self.error('invalid_input', lambda: self.view(verify_source=[f's{i}' for i in range(17)]))


if __name__ == '__main__': unittest.main()
