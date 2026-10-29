"""Declared event time and byte-compatible implicit receipt identity."""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from local_knowledge_wiki.cli import curate, main, review
from local_knowledge_wiki.format import parse, timestamp
from local_knowledge_wiki.requests import digest, encoded
from local_knowledge_wiki.storage import Store, WikiError, capture, init


TIME = '2020-01-02T03:04:05+00:00'
OFFSET = '2020-01-02T12:04:05+09:00'


class ReviewTimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'wiki'
        init(self.bundle)
        self.source = self.root / 'source'
        self.source.write_bytes(b'synthetic evidence')
        self.body = self.root / 'body'
        self.body.write_bytes('보고서\r\n---\nbody'.encode())
        capture(self.bundle, self.source, 'source', 'tool/1', 'synthetic', TIME)
        self.curate()
        self.evidence = 'sources/source/content.raw'

    def curate(self):
        return curate(self.bundle, 'rules', self.body, ['source'], 'tool/1', TIME, 'Concept',
                      '보고서', 'draft', '2030-01-01T00:00:00Z')

    def record(self, key=None, now=None, revision='r000001'):
        return review(self.bundle, 'rules', revision, 'process:test', self.evidence, key, now)

    def snapshot(self):
        return {str(p.relative_to(self.bundle)): p.read_bytes() for p in self.bundle.rglob('*') if p.is_file()}

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', '--error-format', 'json',
                                 *map(str, args)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout if code == 0 else result.stderr)

    def test_cli_explicit_offsets_replay_and_changed_time_or_mode_conflict(self):
        args = ['review', self.bundle, 'rules', '--revision', 'r000001', '--actor', 'process:test',
                '--evidence', self.evidence, '--request-id', 'explicit']
        result = self.cli(*args, '--now', OFFSET)
        self.assertEqual(result['verified'][-1]['at'], TIME)
        self.curate()
        before = self.snapshot()
        for value in (TIME, '2020-01-02T03:04:05Z', '2020-01-02T03:04:05.000000Z'):
            self.assertEqual(self.cli(*args, '--now', value), result)
        self.assertEqual(before, self.snapshot())
        for extra in ([], ['--now', '2020-01-02T03:04:06Z']):
            self.assertEqual(self.cli(*args, *extra, code=2)['error']['code'], 'request_conflict')
            self.assertEqual(before, self.snapshot())
        self.assertIn('r000003', (self.bundle / 'index.md').read_text())

    def test_api_canonical_time_preserves_nel_unknown_metadata_and_exact_body(self):
        original = self.bundle / 'concepts/rules/r000001.md'
        original.write_bytes(original.read_bytes().replace(b'type: Concept',
            b'type: Concept\ndescription: "a\\Nb"\ncustom: {nested: [one, two]}'))
        meta, body = parse(original.read_bytes().decode())
        saved = original.read_bytes()
        result = self.record('api', timestamp(OFFSET))
        self.assertEqual(result['verified'][-1]['at'], TIME)
        stored, new_body = parse((self.bundle / result['revision']).read_bytes().decode())
        stored.pop('verified')
        self.assertEqual(stored, meta)
        self.assertEqual(new_body, body)
        self.assertEqual(original.read_bytes(), saved)
        before = self.snapshot()
        self.assertEqual(self.record('api', TIME), result)
        self.assertEqual(before, self.snapshot())
        shown = self.cli('show', self.bundle, 'rules', '--now', '2029-01-01T00:00:00Z')
        self.assertFalse(shown['stale'])
        self.assertEqual(shown['trust'], 'machine-confirmed')
        self.assertTrue(self.cli('show', self.bundle, 'rules', '--now', '2031-01-01T00:00:00Z')['stale'])

    def test_invalid_explicit_times_fail_before_lock_or_intent_cli_and_api(self):
        args = ['review', self.bundle, 'rules', '--revision', 'r000001', '--actor', 'process:test',
                '--evidence', self.evidence, '--request-id', 'invalid']
        for value in ('', '2020-01-02', '2020-01-02T03:04:05', 'bad', '2020-99-02T03:04:05Z',
                      '0001-01-01T00:00:00+14:00', '9999-12-31T23:59:59-14:00'):
            before = self.snapshot()
            with patch.object(Store, 'lock', side_effect=AssertionError('No lock on invalid input')):
                with self.assertRaises(WikiError) as caught:
                    self.record('invalid', value)
                self.assertEqual(caught.exception.code, 'invalid_input')
            self.assertEqual(self.cli(*args, '--now', value, code=2)['error']['code'], 'invalid_input')
            self.assertEqual(before, self.snapshot())
            self.assertFalse((self.bundle / '.lkw-requests').exists())

    def test_provided_time_needs_no_datetime_now_in_api_or_cli(self):
        clock = Mock()
        clock.now.side_effect = AssertionError('Explicit event time must not require a clock')
        with patch('local_knowledge_wiki.cli.datetime', clock):
            self.assertEqual(self.record(now=OFFSET)['verified'][-1]['at'], TIME)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['review', str(self.bundle), 'rules', '--revision', 'r000002',
                             '--actor', 'process:test', '--evidence', self.evidence, '--now', TIME])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())['verified'][-1]['at'], TIME)
            clock.now.assert_not_called()

    def test_default_actual_utc_clock_and_implicit_explicit_mode_conflict(self):
        low = datetime.now(timezone.utc)
        result = self.record('implicit')
        high = datetime.now(timezone.utc)
        event = timestamp(result['verified'][-1]['at'])
        self.assertLessEqual(low, event)
        self.assertLessEqual(event, high)
        self.assertEqual(event.utcoffset().total_seconds(), 0)
        before = self.snapshot()
        with self.assertRaises(WikiError) as caught:
            self.record('implicit', result['verified'][-1]['at'])
        self.assertEqual(caught.exception.code, 'request_conflict')
        self.assertEqual(before, self.snapshot())

    def test_constructed_legacy_v1_implicit_receipt_replays_with_exact_old_payload(self):
        target = 'concepts/rules/r000001.md'
        original = (self.bundle / target).read_bytes()
        prior_result = self.record()
        # Fixed pre-feature payload shape, independent of new review's implementation.
        legacy_payload = {'id': 'rules', 'revision': 'r000001', 'actor': 'process:test',
                          'evidence': self.evidence,
                          'reference': {'resource': '/' + self.evidence, 'sha256': digest(self.source.read_bytes())},
                          'target_sha256': digest(original)}
        intent = {'version': 1, 'command': 'review',
                  'fingerprint': digest(encoded({'command': 'review', 'payload': legacy_payload}))}
        record = {'intent': intent, 'result': prior_result,
                  'artifacts': {prior_result['revision']: digest((self.bundle / prior_result['revision']).read_bytes())}}
        folder = self.bundle / '.lkw-requests/legacy'
        folder.mkdir(parents=True)
        (folder / 'intent.json').write_bytes(encoded(intent))
        (folder / 'result.json').write_bytes(encoded({**record, 'checksum': digest(encoded(record))}))
        self.curate()
        before = self.snapshot()
        self.assertEqual(self.record('legacy'), prior_result)
        self.assertEqual(before, self.snapshot())
        self.assertIn('r000003', (self.bundle / 'index.md').read_text())

    def test_help_and_no_new_capture_or_curate_clock_option(self):
        result = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', 'review', '--help'],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'--now', result.stdout)
        self.assertIn(b'declared event time', result.stdout)
        self.assertIn('at most 6 fractional-second digits', ' '.join(result.stdout.decode().split()))
        before = self.snapshot()
        for args in (['capture', self.bundle, self.source, '--id', 'new', '--actor', 'tool/1', '--resource', 'synthetic'],
                     ['curate', self.bundle, 'new', '--body', self.body, '--source', 'source', '--actor', 'tool/1']):
            self.assertEqual(self.cli(*args, '--now', TIME, code=2)['error']['code'], 'arguments')
        self.assertEqual(before, self.snapshot())

    def test_overprecision_cli_and_api_reject_before_conversion_lock_or_effects(self):
        values = ('2020-01-02T03:04:05.1234561Z', '2020-01-02T03:04:05.1234569Z',
                  '2020-01-02T03:04:05.123456789Z', '2020-01-02T03:04:05.1234560Z')
        for key in (None, 'overprecision'):
            for value in values:
                with self.subTest(key=key, value=value):
                    before = self.snapshot()
                    args = ['review', self.bundle, 'rules', '--revision', 'r000001', '--actor', 'process:test',
                            '--evidence', self.evidence, '--now', value]
                    if key:
                        args += ['--request-id', key]
                    self.assertEqual(self.cli(*args, code=2)['error']['code'], 'invalid_input')
                    with patch('local_knowledge_wiki.cli.timestamp', side_effect=AssertionError('No conversion')), \
                         patch.object(Store, 'lock', side_effect=AssertionError('No lock')):
                        with self.assertRaises(WikiError) as caught:
                            self.record(key, value)
                        self.assertEqual(caught.exception.code, 'invalid_input')
                    self.assertEqual(before, self.snapshot())
                    self.assertFalse((self.bundle / '.lkw-requests').exists())

    def test_supported_zero_through_six_fractional_digits_record_exact_values(self):
        for width in range(7):
            fraction = '123456'[:width]
            value = '2020-01-02T03:04:05' + ('.' + fraction if width else '') + 'Z'
            expected = '2020-01-02T03:04:05' + ('.' + fraction.ljust(6, '0') if width else '') + '+00:00'
            result = self.record(now=value, revision=f'r{width + 1:06d}')
            self.assertEqual(result['verified'][-1]['at'], expected)

    def test_supported_microseconds_preserve_identity_across_offsets_and_datetime_api(self):
        value = '2020-01-02T03:04:05.123456Z'
        result = self.record('microseconds', value)
        self.assertEqual(result['verified'][-1]['at'], '2020-01-02T03:04:05.123456+00:00')
        self.curate()
        before = self.snapshot()
        self.assertEqual(self.record('microseconds', datetime(2020, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc)), result)
        args = ['review', self.bundle, 'rules', '--revision', 'r000001', '--actor', 'process:test',
                '--evidence', self.evidence, '--request-id', 'microseconds']
        self.assertEqual(self.cli(*args, '--now', '2020-01-02T12:04:05.123456+09:00'), result)
        self.assertEqual(self.cli(*args, '--now', '2020-01-02T03:04:05.123457Z', code=2)['error']['code'], 'request_conflict')
        self.assertEqual(before, self.snapshot())

    def test_shared_parser_historical_metadata_and_readonly_now_are_unchanged(self):
        historical = '2020-01-02T03:04:05.1234569Z'
        self.assertEqual(timestamp(historical).microsecond, 123456)
        original = self.bundle / 'concepts/rules/r000001.md'
        original.write_bytes(original.read_bytes().replace(b'type: Concept',
            ('type: Concept\nverified: {by: "process:historical", at: "' + historical + '"}').encode()))
        result = self.record(now='2020-01-02T03:04:05.123456Z')
        self.assertEqual(result['verified'][0]['at'], historical)
        before = self.snapshot()
        shown = self.cli('show', self.bundle, 'rules', '--now', historical)
        self.assertFalse(shown['stale'])
        self.assertEqual(shown['verified'][0]['at'], historical)
        self.assertEqual(before, self.snapshot())
