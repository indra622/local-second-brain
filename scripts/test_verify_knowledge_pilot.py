"""Saved evidence mutation tests, not model or semantic-quality tests."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import verify_knowledge_pilot as proof


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pilot-proof-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        target = self.root / 'examples/knowledge-practice'
        target.mkdir(parents=True)
        source = proof.ROOT / 'examples/knowledge-practice'
        for name in ('observed-v1', 'v1'):
            shutil.copytree(source / name, target / name)
        self.observed = target / 'observed-v1'

    def test_exact_evidence_passes(self):
        self.assertEqual(proof.verify(self.root)['exact_artifacts'], 10)

    def test_modified_answer_fails(self):
        with (self.observed / 'B-answer.md').open('ab') as file:
            file.write(b' invented')
        with self.assertRaises(AssertionError): proof.verify(self.root)

    def test_changed_readonly_snapshot_even_with_rebound_digest_fails(self):
        import hashlib
        p = self.observed / 'mechanics.json'; value = json.loads(p.read_text())
        snapshot = value['snapshots']['B-after']; first = next(iter(snapshot))
        snapshot[first]['sha256'] = '0' * 64
        value['snapshot_claims']['B-after']['sha256'] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        p.write_text(json.dumps(value))
        with self.assertRaises(AssertionError): proof.verify(self.root)


if __name__ == '__main__': unittest.main()
