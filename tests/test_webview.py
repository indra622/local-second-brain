"""Public synthetic data, real HTTP boundaries and byte-preserving refresh."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from local_knowledge_wiki.storage import Store, WikiError, init, capture
from local_knowledge_wiki.cli import curate
from local_knowledge_wiki.webview import ViewerServer, root_identity, snapshot, Scan, bounded_metadata

NOW = '2026-11-06T00:00:00+00:00'


class WebviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bundle = self.root / 'bundle'
        init(self.bundle)
        self.source = self.root / 'source.txt'
        self.source.write_text('공개 합성 사용자 발언. <script>window.pwned=1</script>')
        capture(self.bundle, self.source, 'input', 'declared/1', 'synthetic', NOW)
        self.body = self.root / 'body.md'
        self.body.write_text('# 처음 생각\n[현재](../topic/r000002.md)\n<script>window.pwned=1</script>')
        self.curate('topic')
        self.body.write_text('# 달라진 생각\n[관계](../other/r000001.md)\n[누락](../missing/r000001.md)\n[공격](javascript:evil)')
        self.curate('topic')
        self.body.write_text('독립된 생각')
        self.curate('other')
        self.identity = root_identity(self.bundle)[1]

    def curate(self, id):
        return curate(self.bundle, id, self.body, ['input'], 'test/1', NOW, 'Concept', id, 'draft', None)

    def get(self):
        return json.loads(snapshot(self.bundle, self.identity))

    def bytes(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes()
                for p in self.bundle.rglob('*') if p.is_file()}

    def test_readonly_history_sources_and_relations(self):
        (self.bundle / '.lkw.lock').unlink()
        before = self.bytes()
        data = self.get()
        self.assertEqual(before, self.bytes())
        self.assertEqual(data['current']['topic'], 'concepts/topic/r000002.md')
        self.assertEqual(len(data['histories']['topic']), 2)
        old = data['notes']['concepts/topic/r000001.md']
        self.assertFalse(old['current'])
        self.assertIn('window.pwned', old['body'])
        self.assertIsNone(old['stale'])
        self.assertEqual(data['sources']['input']['text'], self.source.read_text())
        self.assertTrue(data['sources']['input']['hash_matches_declaration'])
        related = data['notes'][data['current']['topic']]['related']
        self.assertEqual([r['state'] for r in related], ['available', 'unavailable-or-out-of-scope', 'unchecked'])
        self.assertFalse((self.bundle / '.lkw.lock').exists())

    def test_missing_current_not_silently_zero(self):
        (self.bundle / 'concepts/topic/r000002.md').unlink()
        data = self.get()
        self.assertTrue(data['partial'])
        self.assertIn('topic', data['current'])
        self.assertEqual(data['diagnostics'][0]['state'], 'missing-current')

    def test_malformed_metadata_and_provenance(self):
        note = self.bundle / 'concepts/topic/r000002.md'
        note.write_text('---\nstatus: strange\nverified: invalid\n---\n仍是文本')
        (self.bundle / 'sources/input/provenance.json').write_text('[]')
        data = self.get()
        n = data['notes']['concepts/topic/r000002.md']
        self.assertTrue(n['metadata_errors'])
        self.assertIsNone(n['stale'])
        self.assertIn('provenance_error', data['sources']['input'])

    def test_unsafe_source_id_never_reads_neighbor(self):
        p = self.bundle / 'concepts/topic/r000002.md'
        p.write_text('---\ntype: Concept\nsources:\n- id: ../../outside\n---\ntext')
        data = self.get()
        self.assertEqual(data['notes']['concepts/topic/r000002.md']['source_ids'], [])

    def test_symlink_source_and_root_fail_closed(self):
        source = self.bundle / 'sources/input/content.raw'
        source.unlink()
        source.symlink_to(self.source)
        with self.assertRaises((OSError, WikiError)):
            self.get()
        alias = self.root / 'alias'
        alias.symlink_to(self.bundle, target_is_directory=True)
        with self.assertRaises(WikiError):
            root_identity(alias)

    def test_movement_and_bounds_fail_refresh(self):
        original = Scan.stable
        def moved(scan):
            (self.bundle / 'index.md').write_text('changed during scan')
            return original(scan)
        with patch.object(Scan, 'stable', moved):
            with self.assertRaises(WikiError):
                self.get()
        with patch('local_knowledge_wiki.webview.FILE_BYTES', 2):
            with self.assertRaises(WikiError):
                self.get()

    def test_alias_budget_precedes_expansion_and_preserves_scalars(self):
        from datetime import datetime, timezone
        shared = ['leaf']
        for _ in range(15):
            shared = [shared] * 10
        with self.assertRaisesRegex(WikiError, 'traversal limit'):
            bounded_metadata(shared)
        self.assertEqual(bounded_metadata({'at': datetime(2026,1,1,tzinfo=timezone.utc), 7: b'raw'}),
                         {'at': '2026-01-01 00:00:00+00:00', '7': "b'raw'"})
        with self.assertRaisesRegex(WikiError, 'collide'):
            bounded_metadata({1:'one','1':'two'})

    def test_valid_implicit_status_preserves_shared_reader_default(self):
        (self.bundle / 'concepts/topic/r000002.md').write_text('---\ntype: Concept\ntitle: Valid implicit status\n---\nbody')
        n = self.get()['notes']['concepts/topic/r000002.md']
        self.assertEqual(n['metadata_errors'], [])
        self.assertEqual(n['status'], 'stable')

    def test_raw_yaml_alias_expansion_fails_with_bounded_memory(self):
        import tracemalloc
        header = ['type: Concept', 'base: &a [leaf]']
        previous = 'a'
        for letter in 'bcdefghijklmno':
            header.append(letter + ': &' + letter + ' [' + ', '.join(['*'+previous]*10) + ']')
            previous = letter
        (self.bundle / 'concepts/topic/r000002.md').write_text('---\n'+'\n'.join(header)+'\n---\nbody')
        tracemalloc.start()
        try:
            with self.assertRaisesRegex(WikiError, 'traversal limit'):
                self.get()
            self.assertLess(tracemalloc.get_traced_memory()[1], 16 * 1024 * 1024)
        finally:
            tracemalloc.stop()

    def test_source_resource_binding_without_guessing(self):
        path = self.bundle / 'concepts/topic/r000002.md'
        path.write_text('---\ntype: Concept\nsources:\n- id: input\n  resource: https://example.com/source\n- resource: missing\n- id: input\n  resource: ../../sources/different/content.raw\n---\ntext')
        with patch('local_knowledge_wiki.webview.source', side_effect=AssertionError('must not guess')):
            data = self.get_topic_only()
        note = data['notes'][data['current']['topic']]
        self.assertEqual(note['source_ids'], [])
        self.assertEqual(len(note['source_refs']), 3)
        self.assertEqual(note['source_refs'][0]['state'], 'unsupported-or-mismatched-binding')

    def get_topic_only(self):
        (self.bundle / 'concepts/topic/r000001.md').write_text('---\ntype: Concept\n---\nno sources')
        (self.bundle / 'concepts/other/r000001.md').write_text('---\ntype: Concept\n---\nno sources')
        return self.get()

    def test_http_only_exact_origin_and_allowlisted_gets(self):
        before = self.bytes()
        server = ViewerServer(self.bundle)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join()))
        def request(path='/', method='GET', headers=None):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            conn.request(method, path, headers=headers or {})
            res=conn.getresponse(); result=(res.status, dict(res.getheaders()), res.read());conn.close();return result
        status, headers, body = request()
        self.assertEqual(status, 200)
        self.assertIn(b'./app.js', body)
        self.assertIn("default-src 'none'", headers['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(request('/api/snapshot')[0], 200)
        for h in [{'Host':'evil.test'}, {'Origin':'http://evil.test'}, {'Origin':'null'}, {'Sec-Fetch-Site':'cross-site'}]:
            self.assertEqual(request('/api/snapshot', headers=h)[0], 403)
        self.assertEqual(request('/api/snapshot', headers={'Origin':server.origin})[0], 200)
        for path in ['/../../etc/passwd', '/api/file?path=index.md', '/index.md', '/api/snapshot?path=secret']:
            self.assertEqual(request(path)[0], 404)
        for method in ['POST','PUT','PATCH','DELETE','OPTIONS','HEAD']:
            self.assertEqual(request('/api/snapshot',method)[0], 405)
        (self.bundle / 'index.md').write_text('bad index')
        self.assertEqual(request('/api/snapshot')[0], 503)
        self.assertEqual({k:v for k,v in before.items() if k!='index.md'}, {k:v for k,v in self.bytes().items() if k!='index.md'})
