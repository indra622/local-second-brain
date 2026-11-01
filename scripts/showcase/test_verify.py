"""Mutation checks for current QA; no approved repository asset is edited."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CurrentQATests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='showcase-negative-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ('site', 'archive'):
            shutil.copytree(ROOT / name, self.root / name)
        shutil.copytree(ROOT / 'scripts/showcase/fixtures', self.root / 'scripts/showcase/fixtures')
        for name in ('README.md', 'README.ko.md', 'scripts/showcase/preserved-assets.json',
                     'scripts/outcome-video/scene.html', 'scripts/outcome-video/serve.cjs',
                     'scripts/agent-outcome-video/scene.html'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)

    def run_check(self):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/showcase/verify.py')],
                              env={**os.environ, 'SHOWCASE_ROOT': str(self.root)}, capture_output=True)

    def rebind(self, relative):
        # Rebind fixture hashes so semantic/provenance checks must catch the mutation.
        file = self.root / relative
        value = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest = self.root / 'scripts/showcase/preserved-assets.json'
        data = json.loads(manifest.read_text())
        data[relative]['sha256'] = value
        manifest.write_text(json.dumps(data))
        proof = self.root / 'site/data/replay-sha256.json'
        hashes = json.loads(proof.read_text())
        if relative.removeprefix('site/') in hashes:
            hashes[relative.removeprefix('site/')] = value
            proof.write_text(json.dumps(hashes))
            self.rebind('site/data/replay-sha256.json')

    def test_current_passes(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_broken_asset_link_fails(self):
        p = self.root / 'site/index.html'
        p.write_text(p.read_text().replace('assets/logo.png', 'assets/missing.png'))
        self.assertNotEqual(self.run_check().returncode, 0)

    def test_wrong_player_version_fails(self):
        p = self.root / 'site/app.js'
        p.write_text(p.read_text().replace('agent-report-v2-', 'report-scenario-v1-'))
        self.assertNotEqual(self.run_check().returncode, 0)

    def test_wrong_scene_source_fails(self):
        p = self.root / 'scripts/agent-outcome-video/scene.html'
        original = p.read_text()
        changed = original.replace('const TOTAL=acc', 'const TOTAL=34')
        self.assertNotEqual(changed, original)
        p.write_text(changed)
        self.assertNotEqual(self.run_check().returncode, 0)

    def test_rebound_false_excerpt_still_fails(self):
        p = self.root / 'site/data/replay-selection.json'
        data = json.loads(p.read_text()); data[0]['selectedLines'].append('invented proof')
        p.write_text(json.dumps(data)); self.rebind('site/data/replay-selection.json')
        self.assertNotEqual(self.run_check().returncode, 0)

    def test_rebound_false_semantics_still_fails(self):
        p = self.root / 'site/data/sample.json'
        data = json.loads(p.read_text()); data['check']['invalid'] = ['hidden failure']
        p.write_text(json.dumps(data)); self.rebind('site/data/sample.json')
        self.assertNotEqual(self.run_check().returncode, 0)


if __name__ == '__main__': unittest.main()
