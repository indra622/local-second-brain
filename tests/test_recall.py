"""Synthetic current-note retrieval, compatibility, bounds and evidence tests."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

from local_knowledge_wiki.cli import main, search
from local_knowledge_wiki.recall import recall, render
from local_knowledge_wiki.storage import END, START, init, render_entries


NOW = datetime(2026, 10, 29, tzinfo=timezone.utc)


class RecallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'wiki'
        init(self.root)
        self.entries = {}

    def note(self, name, body, revision='r000001', **metadata):
        path = f'concepts/{name}/{revision}.md'
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        meta = {'type': 'Concept', 'status': 'draft', **metadata}
        target.write_text('---\n' + yaml.safe_dump(meta, allow_unicode=True) + '---\n' + body)
        self.entries[name] = path
        (self.root / 'index.md').write_text(START + render_entries(self.entries) + END)
        return target

    def call(self, query, **kwargs):
        return recall(self.root, query, NOW, **kwargs)

    def test_en_ko_pairs_and_false_positives(self):
        cases = [('rename', 'pathlib renames the archive', True),
                 ('보고서', '보고서를 목요일에 보낸다', True),
                 ('규칙', '보관 규칙을 적용한다', True),
                 ('결정', '변경 결정을 기록한다', True),
                 ('규칙 결정', '규칙을 검토하고 결정을 기록한다', True),
                 ('규칙', '규칙성 측정에 대한 별도 연구', True),
                 ('결정', '결정체 구조에 대한 별도 연구', True),
                 ('규칙', '불규칙한 일정', False),
                 ('결정', '미결정 상태', False),
                 ('규', '규칙을 적용한다', False),
                 ('re', 'renames the archive', False),
                 ('가a', '가abc marker', False),
                 ('rename archive', 'pathlib renames the archive', True),
                 ('보고서 목요일', '보고서를 목요일에 보낸다', True),
                 ('rename', 'unrelated xrename marker', False),
                 ('보고서', '중간보고서만 보관', False),
                 ('re', 'renames archive', False),
                 ('port', 'portable equipment', True)]
        for query, body, expected in cases:
            with self.subTest(query=query, body=body):
                self.note('sample', body)
                self.assertEqual(search(self.root, query, NOW), [])
                self.assertEqual(self.call(query, match='exact')['matched'], 0)
                output = self.call(query)
                self.assertEqual(bool(output['matched']), expected)
                self.assertTrue(output['fallback_used'])
                self.assertEqual(output['match_mode'], 'lexical')

    def test_exact_first_multi_term_determinism_and_limit(self):
        self.note('b', 'RENAME archive')
        self.note('a', 'rename archive')
        self.note('prefix', 'renames archives')
        self.note('partial', 'rename')
        output = self.call('Rename archive', limit=1)
        self.assertEqual(output, self.call('Rename archive', limit=1))
        self.assertEqual((output['matched'], output['omitted_results']), (2, 1))
        self.assertEqual(output['results'][0]['id'], 'a')
        self.assertFalse(output['fallback_used'])
        self.assertEqual(self.call('rename archive', match='lexical')['matched'], 3)
        self.assertEqual(len(search(self.root, 'rename archive', NOW)), 2)

    def test_index_selection_read_only_and_full_evidence(self):
        old = self.note('archive', 'renames archive', sources=[{
            'id': 'source', 'resource': '../../sources/source/content.raw'}])
        self.note('archive', 'old irrelevant', revision='r999999')
        self.entries['archive'] = 'concepts/archive/r000001.md'
        (self.root / 'index.md').write_text(START + render_entries(self.entries) + END)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        hit = self.call('rename')['results'][0]
        self.assertEqual((hit['id'], hit['revision']), ('archive', 'r000001'))
        self.assertEqual(hit['sources'][0]['resource'], '../../sources/source/content.raw')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['show', str(self.root), hit['id'], '--revision', hit['revision']]), 0)
        self.assertEqual(json.loads(out.getvalue())['body'], 'renames archive')
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertTrue(old.exists())

    def test_empty_invalid_index_missing_and_invalid_notes(self):
        self.assertEqual(self.call('nothing')['state'], 'empty_index')
        self.assertNotIn('--match lexical', self.call('nothing')['guidance'])
        self.assertIn('--match lexical', self.call('nothing', match='exact')['guidance'])
        target = self.note('sample', 'needle')
        target.unlink()
        output = self.call('needle')
        self.assertEqual(output['state'], 'incomplete')
        self.assertEqual(output['excluded']['unavailable'], 1)
        target.write_bytes(b'\xff')
        self.assertEqual(self.call('needle')['state'], 'incomplete')
        target.write_text('---\ntype: [\n---\nneedle')
        hit = self.call('needle')['results'][0]
        self.assertEqual(hit['trust'], 'invalid-metadata')
        self.assertTrue(hit['metadata_errors'])
        (self.root / 'index.md').write_text('broken')
        self.assertEqual(self.call('needle')['state'], 'invalid_index')
        (self.root / 'index.md').unlink()
        self.assertEqual(self.call('needle')['state'], 'invalid_index')

    def test_lifecycle_trust_freshness_are_declarations(self):
        for status, verified, deadline, trust, stale in [
                ('draft', None, None, 'unverified', None),
                ('deprecated', {'by': 'human:test', 'at': NOW.isoformat()}, '2020-01-01T00:00:00Z', 'human-reviewed', True),
                ('stable', {'by': 'process:test', 'at': NOW.isoformat()}, '2099-01-01T00:00:00Z', 'machine-confirmed', False),
                ('draft', 'broken', 'invalid', 'invalid-metadata', None)]:
            meta = {'stale_after': deadline} if deadline else {}
            if verified is not None:
                meta['verified'] = verified
            self.note('sample', 'needle', status=status, **meta)
            hit = self.call('needle')['results'][0]
            self.assertEqual((hit['status'], hit['trust'], hit['stale']), (status, trust, stale))

    def test_nonfinite_yaml_values_are_safe_standard_json(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            self.note('sample', 'archive', title=value,
                      sources=[{'resource': value}])
            output = self.call('archive')
            hit = output['results'][0]
            self.assertEqual(hit['trust'], 'invalid-metadata')
            self.assertIsNone(hit['title'])
            self.assertIsNone(hit['sources'][0]['resource'])
            self.assertTrue(hit['selected_fields_truncated_or_omitted'])
            def reject_constant(text):
                self.fail('Nonstandard JSON constant: ' + text)
            json.loads(render(output), parse_constant=reject_constant)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(['recall', str(self.root), 'archive']), 0)
            json.loads(out.getvalue(), parse_constant=reject_constant)

    def test_surrogate_yaml_recall_uses_utf8_stdout_with_strict_bounds(self):
        target = self.note('sample', 'archive 보고서 literal \\uD800 ' * 200,
                           title='보고서 \ud800',
                           generated={'by': 'tool/\udfff'},
                           sources=[{'resource': '../../sources/\ud800/content.raw'}])
        self.note('ordinary', 'archive 보존한 원문')
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8:strict',
               'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}
        valid = target.read_text(encoding='utf-8')
        malformed = ('---\ntype: Concept\n"\\uD800": first\n"\\uD800": duplicate\n'
                     '---\narchive 보고서 literal \\uD800\n')
        for document in (valid, malformed):
            target.write_text(document, encoding='utf-8')
            before = {p.relative_to(self.root): p.read_bytes()
                      for p in self.root.rglob('*') if p.is_file()}
            for budget in (2048, 4096, 12000):
                with self.subTest(malformed=document == malformed, budget=budget):
                    process = subprocess.run(
                        [sys.executable, '-m', 'local_knowledge_wiki.cli', 'recall',
                         str(self.root), 'archive', '--max-chars', str(budget)],
                        env=env, capture_output=True, timeout=10)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    self.assertEqual(process.stderr, b'')
                    stdout = process.stdout.decode('utf-8', errors='strict')
                    self.assertLessEqual(len(stdout), budget)
                    output = json.loads(stdout)
                    self.assertEqual(output['matched'], 2)
                    self.assertIn('보고서', stdout)
                    hit = next(item for item in output['results'] if item['id'] == 'sample')
                    if document == valid:
                        self.assertEqual(hit['title'], '보고서 \ud800')
                        self.assertEqual(hit['generated']['by'], 'tool/\udfff')
                        self.assertEqual(hit['sources'][0]['resource'],
                                         '../../sources/\ud800/content.raw')
                        self.assertIn('literal \\uD800', hit['body'])
                    else:
                        self.assertEqual(hit['trust'], 'invalid-metadata')
                        self.assertIn('Duplicate YAML key: \ud800', hit['metadata_errors'])
                    if budget == 2048 and document == valid:
                        self.assertTrue(hit['body_truncated'] or output['omitted_results'])
            self.assertEqual(before, {p.relative_to(self.root): p.read_bytes()
                                     for p in self.root.rglob('*') if p.is_file()})

    def test_surrogates_are_escaped_everywhere_without_escaping_korean(self):
        output = render({'path': '보고서/\ud800', 'body': '결정 \udfff',
                         'context': {'\ud800': '\udfff'}})
        output.encode('utf-8', errors='strict')
        self.assertIn('보고서', output)
        self.assertIn('결정', output)
        self.assertIn('\\ud800', output)
        self.assertIn('\\udfff', output)
        self.assertEqual(json.loads(output)['body'], '결정 \udfff')

    def test_surrogate_escape_expansion_is_included_in_stdout_budget(self):
        self.note('sample', 'archive 보고서 ' * 200, title='\ud800' * 200)
        process = subprocess.run(
            [sys.executable, '-m', 'local_knowledge_wiki.cli', 'recall',
             str(self.root), 'archive', '--max-chars', '2048'],
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8:strict',
                 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')},
            capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        stdout = process.stdout.decode('utf-8', errors='strict')
        self.assertLessEqual(len(stdout), 2048)
        output = json.loads(stdout)
        self.assertEqual(output['matched'], 1)
        self.assertEqual(output['state'], 'budget_omitted')
        self.assertEqual(output['omitted_results'], 1)

    def test_strict_serialized_bounds_and_unknown_metadata(self):
        for i in range(10):
            self.note(f'n{i}', ('가😀e\u0301\t\x01' * 900) + ' needle renames archive',
                      title='needle ' + '가' * 9000,
                      sources=[{'id': 's' * 5000, 'resource': '../' * 5000,
                                'unknown': ['x' * 9000] * 100}] * 20,
                      generated={'by': 'tool/1', 'at': NOW.isoformat(), 'extension': 'x' * 10000},
                      extension={'deep': ['x' * 9000] * 100})
        for budget in (2048, 3000, 12000, 50000):
            result = self.call('needle', max_chars=budget, limit=10)
            self.assertLessEqual(len(render(result)), budget)
            self.assertEqual(result['matched'], 10)
            self.assertTrue(result['omitted_results'] or any(x['body_truncated'] for x in result['results']))
            for item in result['results']:
                self.assertTrue(item['metadata_omitted'])
                self.assertTrue(item['selected_fields_truncated_or_omitted'])
        result = self.call('needle')
        self.assertNotIn('extension', render(result))

    def test_body_window_and_source_paths_are_data(self):
        self.note('sample', 'unrelated ' * 1000 + 'renames archive',
                  sources=[{'resource': '../../../../private/secret'},
                           {'resource': 'https://example.invalid/never-fetch'}])
        hit = self.call('rename')['results'][0]
        self.assertGreater(hit['body_start'], 0)
        self.assertIn('renames', hit['body'])
        self.assertTrue(hit['body_truncated'])
        self.assertEqual(hit['sources'][0]['resource'], '../../../../private/secret')
        target = self.root / self.entries['sample']
        target.unlink()
        target.symlink_to('/nonexistent')
        self.assertEqual(self.call('rename')['excluded']['unavailable'], 1)

    def test_cli_help_errors_and_actual_budget(self):
        self.note('sample', 'needle ' * 10000)
        for args, code in [(['needle', '--max-chars', '2048'], 0),
                           (['!!!'], 2), (['needle', '--limit', '0'], 2),
                           (['needle', '--max-chars', '100'], 2),
                           (['needle', '--format', 'text'], 2)]:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    actual = main(['recall', str(self.root), *args])
                except SystemExit as exc:
                    actual = exc.code
            self.assertEqual(actual, code, err.getvalue())
            if code == 0:
                self.assertLessEqual(len(out.getvalue()), 2048)
                self.assertEqual(json.loads(out.getvalue())['matched'], 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            main(['recall', '--help'])
        self.assertIn('not tokens', out.getvalue())
        self.assertNotIn('--format', out.getvalue())


if __name__ == '__main__':
    unittest.main()
