"""Synthetic typed assertions, graph scope/parser/path and bounded packing behavior."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_knowledge_wiki import annotations
from local_knowledge_wiki.cli import annotate, curate, main
from local_knowledge_wiki.context import context
from local_knowledge_wiki.errors import WikiError
from local_knowledge_wiki.format import parse, serialize_revision
from local_knowledge_wiki.graph import graph, markdown_links
from local_knowledge_wiki.recall import render
from local_knowledge_wiki.storage import END, START, Store, capture, init, render_entries


AT = '2026-11-01T12:00:00+00:00'


def relation(target='b', kind='depends_on', ident='edge', expectation='required', revision=None):
    endpoint = {'id': target}
    if revision is not None:
        endpoint['revision'] = revision
    return {'id': ident, 'type': kind, 'target': endpoint, 'expectation': expectation, 'evidence': []}


def context_data():
    return {'work_id': 'task', 'recipients': ['all'], 'completed': [], 'decisions': [],
            'open_questions': [], 'lessons': []}


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'wiki'
        init(self.bundle)
        self.source = self.root / 'source'
        self.source.write_bytes(b'synthetic source')
        capture(self.bundle, self.source, 'source', 'test/1', 'synthetic', AT)
        self.file = self.root / 'annotations.json'
        self.body = self.root / 'body'
        self.body.write_text('Synthetic body\r\n결정\n')

    def note(self, name, items=None, body=None, ctx=False):
        if body is not None:
            self.body.write_text(body)
        value = {'version': 1}
        if items is not None:
            value['relations'] = {'items': items}
        if ctx:
            value['context'] = context_data()
        self.file.write_text(json.dumps(value))
        return curate(self.bundle, name, self.body, ['source'], 'test/1', AT, 'Concept', name,
                      'draft', None, annotations_file=self.file if len(value) > 1 else None)

    def snapshot(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*') if p.is_file()}

    def error(self, code, fn):
        with self.assertRaises(WikiError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)

    def view(self, **kwargs):
        return graph(self.bundle, max_chars=1000000, **kwargs)

    def test_relation_authoring_both_sections_update_replay_and_cas(self):
        original_path = self.note('a', [relation()], ctx=True)
        original = (self.bundle / original_path).read_bytes()
        update = {'items': [relation('c', kind='supports')]}
        self.file.write_text(json.dumps(update))
        args = (self.bundle, 'a', 'r000001', 'relations', self.file, 'process:test')
        result = annotate(*args, now=AT, request_id='update')
        meta, body = parse((self.bundle / result['revision']).read_bytes().decode())
        old, old_body = parse(original.decode())
        self.assertEqual(body, old_body)
        self.assertEqual(meta[annotations.KEY]['context'], old[annotations.KEY]['context'])
        self.assertEqual(meta[annotations.KEY]['relations']['data'], update)
        self.assertEqual((self.bundle / original_path).read_bytes(), original)
        before = self.snapshot()
        self.assertEqual(annotate(*args, now='2026-11-01T21:00:00+09:00', request_id='update'), result)
        self.error('precondition_failed', lambda: annotate(*args, now=AT, request_id='stale'))
        self.file.write_bytes(self.file.read_bytes() + b' ')
        self.error('request_conflict', lambda: annotate(*args, now=AT, request_id='update'))
        self.assertEqual(before, self.snapshot())

    def test_invalid_new_relations_fail_without_effects(self):
        self.note('a')
        before = self.snapshot()
        cases = [relation('a'), relation(kind='caused'), relation(expectation='maybe'),
                 relation(expectation='wanted', revision='r000001'), relation(revision='r000000')]
        for item in cases:
            self.file.write_text(json.dumps({'items': [item]}))
            self.error('invalid_input', lambda: annotate(self.bundle, 'a', 'r000001', 'relations', self.file,
                                                        'test/1', AT, 'invalid'))
            self.assertEqual(before, self.snapshot())
        for items in ([relation(), relation()], [relation(ident=f'e{i}') for i in range(129)]):
            self.file.write_text(json.dumps({'items': items}))
            self.error('invalid_input', lambda: annotate(self.bundle, 'a', 'r000001', 'relations', self.file, 'test/1', AT, 'invalid'))
            self.assertEqual(before, self.snapshot())
        self.file.write_text(json.dumps({'items': [relation()]}))
        for limit in ('SECTION_BYTES', 'ROOT_BYTES'):
            with patch.object(annotations, limit, 1):
                self.error('input_too_large', lambda: annotate(self.bundle, 'a', 'r000001', 'relations', self.file, 'test/1', AT, 'limit'))
            self.assertEqual(before, self.snapshot())
        self.file.write_text(json.dumps({'version': 1, 'relations': {'items': [relation('new')]}}))
        self.error('invalid_input', lambda: self.note('new', [relation('new')]))
        self.assertEqual(before, self.snapshot())

    def test_overview_backlinks_grouping_and_provenance(self):
        self.note('a', [relation(ident='first'), relation(ident='second')],
                  '[B](../b/r000001.md) and [B again](../b/r000001.md)\n')
        b = self.note('b', body='Target')
        output = self.view()
        declared = next(e for e in output['edges'] if e['origin'] == 'annotation')
        self.assertEqual(declared['count'], 2)
        self.assertEqual([p['id'] for p in declared['provenance']], ['first', 'second'])
        self.assertTrue(declared['traversable'])
        self.assertEqual(declared['target_path'], b)
        self.assertEqual(len(declared['target_sha256']), 64)
        self.assertEqual(len(declared['from']['sha256']), 64)
        self.assertEqual(declared['provenance'][0]['recorded_at'], AT)
        markdown = next(e for e in output['edges'] if e['origin'] == 'markdown')
        self.assertEqual(markdown['count'], 2)
        self.assertEqual(len(markdown['provenance']), 2)
        sources = [e for e in output['edges'] if e['origin'] == 'sources']
        self.assertEqual(len(sources), 2)
        self.assertTrue(all(e['resolution'] == 'unchecked_resource' for e in sources))
        self.assertEqual({e['origin'] for e in self.view(backlinks='b')['edges']}, {'annotation', 'markdown'})
        self.assertEqual([e['type'] for e in self.view(relation=['depends_on'])['edges']], ['depends_on'])
        self.assertEqual(output, self.view())

    def test_scope_current_history_wanted_and_missing_targets_are_distinct(self):
        self.note('a', [relation('b'), relation('b', ident='pin', revision='r000001'),
                        relation('planned', ident='wanted', expectation='wanted'),
                        relation('unknown', ident='required'), relation('broken', ident='missing')])
        self.note('b', body='old'); current = self.note('b', body='current')
        broken = self.note('broken'); (self.bundle / broken).unlink()
        before = self.snapshot()
        output = self.view()
        states = {e['provenance'][0]['id']: e['resolution'] for e in output['edges'] if e['origin'] == 'annotation'}
        self.assertEqual(states, {'edge': 'resolved', 'pin': 'non_current_reference', 'wanted': 'wanted_not_indexed',
                                  'required': 'not_indexed', 'missing': 'missing_indexed'})
        original_read = Store.read
        opened = []
        def read(store, path, *args, **kwargs):
            opened.append(path)
            return original_read(store, path, *args, **kwargs)
        with patch.object(Store, 'read', read):
            scoped = self.view(scope=['a'], relation=['depends_on'])
        self.assertEqual(set(opened), {'index.md', 'concepts/a/r000001.md'})
        self.assertTrue(all(e['resolution'] == 'out_of_scope' for e in scoped['edges'] if e['target']['id'] in ('b', 'broken')))
        self.assertNotIn('concepts/b/r000001.md', opened)
        self.assertNotIn(current, opened)
        self.assertEqual(before, self.snapshot())
        self.error('not_found', lambda: self.view(scope=['absent']))
        self.error('invalid_input', lambda: self.view(scope=['a'], path=['a', 'b']))

    def test_shortest_directed_paths_cycles_ties_depth_and_partial_truth(self):
        self.note('a', [relation('c', ident='c'), relation('b', ident='b')])
        self.note('b', [relation('d')]); self.note('c', [relation('d')])
        self.note('d', [relation('a')])
        output = self.view(path=['a', 'd'], relation=['depends_on'])
        self.assertEqual(output['path_state'], 'found')
        self.assertEqual(output['path_length'], 2)
        steps = output['paths'][0]['steps']
        self.assertEqual([e['target']['id'] for e in steps], ['b', 'd'])
        self.assertTrue(output['paths'][0]['shortest_proven'])
        self.assertEqual(self.view(path=['a', 'd'], max_depth=1)['path_state'], 'no_path_within_depth')
        self.assertEqual(self.view(path=['a', 'a'])['path_length'], 0)
        self.assertEqual(self.view(path=['d', 'b'])['path_length'], 2)
        with patch('local_knowledge_wiki.graph.NOTE_LIMIT', 3):
            partial = self.view(path=['a', 'd'])
            self.assertEqual(partial['path_state'], 'undetermined')
        self.note('missing'); (self.bundle / 'concepts/missing/r000001.md').unlink()
        partial = self.view(path=['a', 'd'])
        self.assertEqual(partial['path_state'], 'found_partial')
        self.assertFalse(partial['paths'][0]['shortest_proven'])

    def test_graph_parser_code_boundaries_and_legacy_parser_unchanged(self):
        text = ('[one](one.md) ` [hidden](code.md) ` [two](two.md)\n'
                '`` [hidden](code.md) ` still code `` [three](three.md)\n'
                'unmatched ` [four](four.md)\n'
                '~~~python\n[fenced](code.md)\n```\n~~~\n'
                '```lang\n[fenced](code.md)\n``` trailing text\n[still fenced](code.md)\n```\n'
                '[five](five.md)\n``multiline\n[hidden](code.md)\n`` [six](six.md)\n')
        self.assertEqual([r for r, _ in markdown_links(text)],
                         ['one.md', 'two.md', 'three.md', 'four.md', 'five.md', 'six.md'])
        self.assertEqual(list(markdown_links('```\n[hidden](code.md)')), [])
        self.assertEqual(list(markdown_links('[x](a.md)\n')), [('a.md', 1)])
        from local_knowledge_wiki.format import links
        self.assertIn('code.md', list(links('`[example](code.md)`')))

    def test_parser_line_provenance_for_lf_crlf_and_cr(self):
        for ending in ('\n', '\r\n', '\r'):
            body = ending.join(['~~~', 'ignored', '~~~', '[text](../b/r000001.md)',
                                '``multiline', '[hidden](code.md)', '``', '[last](last.md)', ''])
            with self.subTest(ending=repr(ending)):
                self.assertEqual(list(markdown_links(body)), [('../b/r000001.md', 4), ('last.md', 8)])

    def test_section_local_readers_preserve_unrelated_valid_data(self):
        p = self.note('a', [relation()], ctx=True); self.note('b')
        target = self.bundle / p
        meta, body = parse(target.read_text())
        meta[annotations.KEY]['relations']['data']['items'][0]['type'] = 'unsupported'
        target.write_bytes(serialize_revision(meta, body))
        output = context(self.bundle, scope=['a'], now=AT)
        self.assertEqual(output['matched_total'], 1)
        self.assertEqual(output['results'][0]['data']['work_id'], 'task')
        self.assertEqual(output['diagnostics'][0]['kind'], 'invalid_relations')
        self.assertFalse(output['diagnostics'][0]['affects_analysis'])
        self.assertEqual(self.view(path=['a', 'b'])['path_state'], 'undetermined')
        meta[annotations.KEY]['relations']['data']['items'][0]['type'] = 'depends_on'
        meta[annotations.KEY]['context']['data']['recipients'] = []
        target.write_bytes(serialize_revision(meta, body))
        output = self.view(path=['a', 'b'])
        self.assertEqual(output['path_state'], 'found')
        self.assertEqual(output['diagnostics'][0]['kind'], 'invalid_context')
        self.assertFalse(output['diagnostics'][0]['affects_analysis'])
        meta[annotations.KEY]['version'] = True
        target.write_bytes(serialize_revision(meta, body))
        self.assertEqual(context(self.bundle, scope=['a'], now=AT)['results'], [])
        self.assertEqual(self.view(path=['a', 'b'])['path_state'], 'undetermined')

    def test_limits_read_failures_and_no_raw_evidence_access(self):
        self.note('a', [relation()], '[bad](../../../../secret)\n[asset](../../sources/source/content.raw)\n')
        self.note('b')
        before = self.snapshot()
        with patch('local_knowledge_wiki.graph.READ_BYTES', 1):
            output = self.view()
            self.assertFalse(output['scan']['complete'])
            self.assertIsNone(output['scan']['read_bytes'])
        with patch('local_knowledge_wiki.graph.REFERENCE_LIMIT', 1):
            output = self.view()
            self.assertFalse(output['scan']['complete'])
            self.assertEqual(output['scan']['references'], 1)
            self.assertIsNone(output['counts']['edges_total'])
        with patch('local_knowledge_wiki.graph.DIAGNOSTIC_LIMIT', 0):
            output = self.view()
            self.assertGreater(output['omitted']['diagnostics'], 0)
        self.assertEqual(before, self.snapshot())
        (self.bundle / '.lkw.lock').unlink()
        self.view()
        self.assertFalse((self.bundle / '.lkw.lock').exists())

    def test_large_report_packing_is_bounded_whole_and_uses_few_formatting_passes(self):
        self.note('a', body='\n'.join(f'[asset](../../assets/item-{i}.txt)' for i in range(10000)))
        import local_knowledge_wiki.graph as module
        original = module.render
        calls = []
        def rendered(value):
            calls.append(1)
            return original(value)
        with patch.object(module, 'render', rendered):
            result = graph(self.bundle, relation=['link'], max_chars=2048)
        self.assertLessEqual(len(render(result)), 2048)
        self.assertEqual(result['counts']['edges_total'], 10000)
        self.assertEqual(result['omitted']['edges'], 10000 - len(result['edges']))
        self.assertLess(len(calls), 60)
        for edge in result['edges']:
            self.assertEqual(len(edge['from']['sha256']), 64)
            self.assertTrue(edge['target']['resource'].endswith('.txt'))
        for budget in (2048, 3000, 12000):
            result = graph(self.bundle, relation=['link'], max_chars=budget)
            self.assertLessEqual(len(render(result)), budget)

    def test_long_id_minimum_budget_path_record_and_index_change(self):
        first, second = 'a' * 64, 'b' * 64
        self.note(first, [relation(second)])
        self.note(second)
        for options in ({}, {'backlinks': second}, {'path': [first, second]}):
            report = graph(self.bundle, scope=[first, second], max_chars=2048, **options)
            self.assertLessEqual(len(render(report)), 2048)
            self.assertEqual(report['query']['endpoints'], list(options.get('path', [second] if options.get('backlinks') else [])))
            if options.get('path'):
                self.assertEqual(report['path_state'], 'found')
                self.assertEqual(report['omitted']['paths'], 1 - len(report['paths']))
        original = Store.read
        index_reads = []
        def read(store, path, *args, **kwargs):
            if path == 'index.md':
                index_reads.append(path)
                if len(index_reads) == 2:
                    return b'changed index'
            return original(store, path, *args, **kwargs)
        with patch.object(Store, 'read', read):
            report = self.view(path=[first, second])
        self.assertTrue(report['index_changed'])
        self.assertEqual(report['path_state'], 'found_partial')
        self.assertIsNone(report['counts']['edges_total'])

    def test_graph_rejects_symlinks_and_counts_invalid_references_toward_cap(self):
        self.note('a', body='\n'.join('[bad](../../../../secret)' for _ in range(5)))
        self.note('b')
        target = self.bundle / 'concepts/b/r000001.md'
        target.unlink(); target.symlink_to(self.source)
        with patch('local_knowledge_wiki.graph.REFERENCE_LIMIT', 2):
            report = self.view(relation=['link'])
            self.assertEqual(report['scan']['references'], 2)
            self.assertFalse(report['scan']['complete'])
        report = self.view(scope=['b'])
        self.assertEqual(report['nodes'][0]['availability'], 'unavailable_indexed')
        self.assertFalse(report['scan']['complete'])
        (self.bundle / 'index.md').write_text('bad index')
        self.error('invalid_index', self.view)

    def test_cli_errors_and_unsupported_execution(self):
        for options in (['--path', 'a', 'b', '--backlinks', 'a'], ['--max-depth', '3'],
                        ['--relation', 'unknown'], ['--max-chars', '100']):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                try:
                    code = main(['--error-format', 'json', 'graph', str(self.bundle), *options])
                except SystemExit as exc:
                    code = exc.code
            self.assertEqual(code, 2)
            self.assertIsInstance(json.loads(err.getvalue())['error'], dict)
        with patch('local_knowledge_wiki.platform.sys.platform', 'win32'), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['graph', str(self.bundle)]), 2)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(['graph', '--help'])
        self.assertEqual(caught.exception.code, 0)


if __name__ == '__main__':
    unittest.main()
