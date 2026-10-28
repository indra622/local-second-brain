"""Run each README and its continuation guide in a fresh project copy."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def verify_readme(project, readme):
    guide = 'docs/getting-started.ko.md' if readme == 'README.ko.md' else 'docs/getting-started.md'
    documents = (readme, guide)
    blocks = [block for document in documents
              for block in re.findall(r'```sh\n(.*?)```', (project / document).read_text(), re.DOTALL)]
    with tempfile.TemporaryDirectory(prefix='lkw-quickstart-', dir=project) as temporary:
        root = Path(temporary)
        for name in ('src', 'tests', 'docs', 'examples', 'templates', 'workflows'):
            shutil.copytree(project / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('README.md', 'README.ko.md', 'pyproject.toml', 'LICENSE'):
            shutil.copy2(project / name, root / name)
        tmp = root / 'tmp'
        tmp.mkdir()
        home = root / 'home'
        home.mkdir()
        env = {**os.environ, 'HOME': str(home), 'TMPDIR': str(tmp),
               'PIP_CACHE_DIR': str(root / 'pip-cache'), 'PYTHONUSERBASE': str(home / 'python'),
               'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
        result = subprocess.run(['sh', '-c', 'set -eu\n' + '\n'.join(blocks)], cwd=root, env=env, timeout=600)
        if result.returncode:
            raise SystemExit(result.returncode)
        bundles = list(tmp.glob('*/wiki'))
        assert len(bundles) == 1, bundles
        bundle = bundles[0]
        assert (bundle / 'sources/report-memo-1/content.raw').read_bytes() == (
            root / 'examples/inputs/report-memo-1.txt').read_bytes()
        assert (bundle / 'sources/report-memo-2/content.raw').read_bytes() == (
            root / 'examples/inputs/report-memo-2.txt').read_bytes()
        assert len(list((bundle / 'concepts/report-rules').glob('r*.md'))) == 3
        index = (bundle / 'index.md').read_text()
        assert 'r000003.md' in index and 'r000001.md' not in index and 'r000002.md' not in index
        assert not (bundle / '.lkw.lock').exists()
        executable = root / '.venv/bin/second-brain'

        def read(*args):
            output = subprocess.check_output([str(executable), args[0], str(bundle), *args[1:]],
                                             cwd=root, env=env, text=True, timeout=30)
            return json.loads(output)

        history = read('history', 'report-rules')
        assert [note['current'] for note in history] == [False, False, True]
        assert read('list') == history
        assert read('show', 'report-rules')['body'] == (root / 'examples/inputs/report-v2.md').read_text()
        assert read('show', 'report-rules', '--revision', 'r000001')['body'] == (
            root / 'examples/inputs/report-v1.md').read_text()
        reviewed = read('show', 'report-rules', '--revision', 'r000002')
        assert reviewed['body'] == read('show', 'report-rules', '--revision', 'r000001')['body']
        assert reviewed['trust'] == 'human-reviewed' and reviewed['status'] == 'draft'
        assert read('show', 'report-rules')['trust'] == 'unverified'
        assert 'verified' not in read('show', 'report-rules')['metadata']
        event = reviewed['verified'][0]
        target = bundle / 'concepts/report-rules/r000001.md'
        assert event['x-second-brain-target']['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
        assert event['x-second-brain-evidence']['sha256'] == hashlib.sha256(
            (bundle / 'sources/report-memo-1/content.raw').read_bytes()).hexdigest()
        diff = read('diff', 'report-rules', 'r000001', 'r000003')['diff']
        assert '--- concepts/report-rules/r000001.md' in diff and '+++ concepts/report-rules/r000003.md' in diff
        assert '-Send the weekly report on Friday.' in diff
        assert '+Send the weekly report on Thursday.' in diff
        assert read('show', 'report-rules')['metadata']['sources'][0]['id'] == 'report-memo-2'
        hits = read('search', 'report')
        assert len(hits) == 3 and all('snippet' in hit for hit in hits)
        current = read('search', 'report', '--current-only', '--status', 'draft', '--freshness', 'unknown')
        assert len(current) == 1 and current[0]['path'].endswith('r000003.md')
        fresh = read('search', 'report', '--freshness', 'fresh', '--now', '2026-10-27T00:00:00Z')
        assert len(fresh) == 2 and all(hit['path'].endswith(('r000001.md', 'r000002.md')) for hit in fresh)
        demo = bundle.parent / 'reuse-demo'
        summary = json.loads((demo / 'summary.json').read_text())
        assert summary['initial_hits'] == 0 and summary['revisions'] == 3
        assert summary['current'] == 'concepts/lantern/r000003.md'
        assert summary['trust'] == 'unverified'
        assert summary['check'] == {'invalid': [], 'warnings': [], 'stale': [], 'concepts': 3}
        before = json.loads((demo / 'reuse-before.json').read_text())
        after = json.loads((demo / 'reuse-after.json').read_text())
        assert 'amber trays and two bells' in before['body']
        assert 'cobalt trays and three bells' in after['body']
        assert before['reused_revision'].endswith('r000002.md')
        assert after['reused_revision'].endswith('r000003.md')
        assert (demo / 'wiki/sources/lantern-v1/content.raw').read_bytes() == (
            root / 'examples/reuse-inputs/source-v1.txt').read_bytes()
        print(f'{readme} + {guide}: install + workflow + revisions + browsing/filters + reuse demo: PASS')


def main():
    project = Path(__file__).resolve().parents[1]
    for readme in ('README.md', 'README.ko.md'):
        verify_readme(project, readme)


if __name__ == '__main__':
    main()
