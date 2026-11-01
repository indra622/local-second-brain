"""Explicit judgments, delivered-output metrics and one-pass raw recall compatibility."""

import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import test_graph as fixtures
from local_knowledge_wiki.cli import main
from local_knowledge_wiki.evaluation import evaluate
from local_knowledge_wiki.recall import recall, render
from local_knowledge_wiki.storage import Store

AT = '2026-11-02T12:00:00Z'


class EvaluationTests(unittest.TestCase):
    setUp = fixtures.GraphTests.setUp
    note = fixtures.GraphTests.note
    snapshot = fixtures.GraphTests.snapshot
    error = fixtures.GraphTests.error

    def cases(self, gold=None, query='needle', **kwargs):
        value = {'version': 1, 'target_mode': 'current_id', 'cases': [
            {'id': 'question', 'query': query, 'gold': gold if gold is not None else [{'id': 'a'}], **kwargs}]}
        self.file.write_text(json.dumps(value))
        return value

    def view(self, **kwargs):
        return evaluate(self.bundle, self.file, now=AT, max_chars=1000000, **kwargs)

    def test_multiple_golds_full_denominator_and_modes_delivered_equivalence(self):
        self.note('a', body='needle'); self.note('b', body='unrelated')
        self.cases([{'id': 'a'}, {'id': 'b'}])
        result = self.view(mode=['exact:frequency', 'auto:bm25'], k=[1, 3])
        for summary in result['summaries']:
            self.assertEqual(summary['metrics']['recall_at'], {'1': .5, '3': .5})
            self.assertEqual(summary['metrics']['mrr_at_k'], 1)
        self.assertEqual(result['cases'][0]['modes']['exact:frequency']['missing_gold'], ['concepts/b/r000001.md'])
        self.assertEqual(result['summaries'][1]['comparison_to_first']['unchanged'], 1)

    def test_invalid_labels_null_all_aggregates_not_successful_subset(self):
        self.note('a', body='needle'); self.note('b', body='needle')
        value = self.cases()
        value['cases'].append({'id': 'bad', 'query': 'needle', 'gold': [{'id': 'missing'}]})
        self.file.write_text(json.dumps(value))
        result = self.view()
        self.assertIsNone(result['summaries'][0]['metrics'])
        self.assertIsNotNone(result['cases'][0]['modes']['auto:frequency']['metrics'])
        self.assertFalse(result['analysis_complete'])
        self.cases([{'id': 'b'}])
        self.assertEqual(self.view(scope=['a'])['cases'][0]['errors'][0]['reason'], 'gold_out_of_scope')
        value = self.cases([{'id': 'a', 'revision': 'r999999'}]); value['target_mode'] = 'exact_revision'
        self.file.write_text(json.dumps(value))
        self.assertEqual(self.view()['cases'][0]['errors'][0]['reason'], 'gold_not_current')
        value['cases'][0]['gold'] = [{'id': 'a', 'revision': 'r000001', 'sha256': '0' * 64}]
        self.file.write_text(json.dumps(value))
        self.assertEqual(self.view()['cases'][0]['errors'][0]['reason'], 'gold_hash_mismatch')

    def test_strict_cases_duplicate_gold_and_control_metrics(self):
        self.note('a', body='needle')
        value = self.cases([{'id': 'a'}, {'id': 'a'}])
        self.error('invalid_input', self.view)
        self.cases([], query='absent', expect_no_match=True)
        result = self.view()
        self.assertIsNone(result['summaries'][0]['metrics'])
        self.assertEqual(result['summaries'][0]['no_match_accuracy'], 1)
        self.file.write_text('{"version":1,"version":1}')
        self.error('invalid_input', self.view)
        self.file.write_text('{"value":NaN}')
        self.error('invalid_input', self.view)
        self.cases()
        self.error('invalid_input', lambda: self.view(k=[0]))
        self.error('invalid_input', lambda: self.view(mode=['external']))

    def test_scoped_corpus_read_once_and_current_not_highest(self):
        p = self.note('a', body='needle')
        self.note('b', body='private excluded')
        (self.bundle / 'concepts/a/r999999.md').write_text('not current')
        self.cases()
        original = Store.read; paths = []
        def read(store, path, *args, **kwargs):
            paths.append(path)
            return original(store, path, *args, **kwargs)
        before = self.snapshot()
        with patch.object(Store, 'read', read):
            result = self.view(scope=['a'], mode=['auto:frequency', 'exact:bm25', 'lexical:frequency'])
        self.assertEqual(paths, [self.file.name, 'index.md', p, 'index.md'])
        self.assertFalse(result['partial'])
        self.assertEqual(before, self.snapshot())
        for method in result['cases'][0]['modes'].values():
            self.assertEqual(method['delivered'], [p])
        again = self.view(scope=['a'])
        self.assertEqual(result['identity'], again['identity'])

    def test_corpus_unavailable_and_cap_incomplete_never_primary_success(self):
        self.note('a', body='needle'); p = self.note('b', body='unused')
        self.cases()
        (self.bundle / p).unlink()
        result = self.view()
        self.assertFalse(result['scan']['complete'])
        self.assertIsNone(result['summaries'][0]['metrics'])
        with patch('local_knowledge_wiki.evaluation.READ_BYTES', 1):
            result = self.view(scope=['a'])
            self.assertLessEqual(result['scan']['budget_charged_bytes'], 1)
            self.assertIsNone(result['scan']['read_bytes'])
            self.assertIsNone(result['summaries'][0]['metrics'])

    def test_delivered_budget_omissions_and_report_omissions_are_separate(self):
        self.note('a', body='needle')
        p = self.bundle / 'concepts/a/r000001.md'
        from local_knowledge_wiki.format import parse, serialize_revision
        meta, body = parse(p.read_text()); meta['title'] = '\ud800' * 200
        p.write_bytes(serialize_revision(meta, body))
        self.cases()
        result = self.view(result_max_chars=2048)
        row = result['cases'][0]['modes']['auto:frequency']
        self.assertEqual(row['state'], 'budget_omitted')
        self.assertEqual(row['metrics']['recall_at']['10'], 0)
        self.assertEqual(row['reason'], 'budget_omitted')
        for budget in (2048, 3000):
            report = evaluate(self.bundle, self.file, now=AT, max_chars=budget)
            self.assertLessEqual(len(render(report)), budget)
            self.assertEqual(report['counts']['cases'], 1)

    def test_case_input_byte_boundary_and_index_change(self):
        self.note('a', body='needle'); self.cases()
        from local_knowledge_wiki.evaluation import CASE_BYTES
        raw = self.file.read_bytes()
        self.file.write_bytes(raw + b' ' * (CASE_BYTES - len(raw)))
        self.assertTrue(self.view()['analysis_complete'])
        self.file.write_bytes(self.file.read_bytes() + b' ')
        with patch('local_knowledge_wiki.evaluation.json.loads', side_effect=AssertionError('parsed before size rejection')):
            self.error('input_too_large', self.view)
        self.cases()
        original = Store.read; indices = []
        def read(store, path, *args, **kwargs):
            if path == 'index.md':
                indices.append(path)
                if len(indices) == 2: return b'changed index'
            return original(store, path, *args, **kwargs)
        with patch.object(Store, 'read', read): result = self.view()
        self.assertTrue(result['index_changed'])
        self.assertIsNone(result['summaries'][0]['metrics'])

    def test_prefix_controls_invalid_metadata_and_actual_cli(self):
        p = self.note('a', body='보고서를 보낸다 renames archives')
        self.cases(query='보고서')
        result = self.view(mode=['exact:frequency', 'auto:frequency', 'lexical:bm25'])
        self.assertEqual(result['summaries'][0]['metrics']['mrr_at_k'], 0)
        self.assertEqual(result['summaries'][1]['metrics']['mrr_at_k'], 1)
        self.assertEqual(result['summaries'][1]['comparison_to_first']['improved'], 1)
        (self.bundle / p).write_text('---\ntype: [\n---\n보고서를 보낸다')
        self.assertEqual(self.view()['summaries'][0]['metrics']['mrr_at_k'], 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['eval-retrieval', str(self.bundle), '--cases', str(self.file), '--now', AT]), 0)
        self.assertEqual(json.loads(out.getvalue())['command'], 'eval-retrieval')


if __name__ == '__main__': unittest.main()
