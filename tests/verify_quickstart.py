"""Run the README shell blocks in a fresh, disposable project copy."""

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def verify_readme(project, readme):
    blocks = re.findall(r'```sh\n(.*?)```', (project / readme).read_text(), re.DOTALL)
    with tempfile.TemporaryDirectory(prefix='lkw-quickstart-', dir=project) as temporary:
        root = Path(temporary)
        for name in ('src', 'tests', 'docs', 'examples', 'templates', 'workflows'):
            shutil.copytree(project / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('README.md', 'README.ko.md', 'pyproject.toml'):
            shutil.copy2(project / name, root / name)
        tmp = root / 'tmp'
        tmp.mkdir()
        home = root / 'home'
        home.mkdir()
        env = {**os.environ, 'HOME': str(home), 'TMPDIR': str(tmp),
               'PIP_CACHE_DIR': str(root / 'pip-cache'), 'PYTHONUSERBASE': str(home / 'python'),
               'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
        result = subprocess.run(['sh', '-c', 'set -eu\n' + '\n'.join(blocks)], cwd=root, env=env)
        if result.returncode:
            raise SystemExit(result.returncode)
        bundles = list(tmp.glob('*/wiki'))
        assert len(bundles) == 1, bundles
        bundle = bundles[0]
        assert (bundle / 'sources/garden-note/content.raw').read_bytes() == (
            root / 'examples/inputs/garden-note.txt').read_bytes()
        assert len(list((bundle / 'concepts/garden').glob('r*.md'))) == 2
        index = (bundle / 'index.md').read_text()
        assert 'r000002.md' in index and 'r000001.md' not in index
        assert not (bundle / '.lkw.lock').exists()
        executable = root / '.venv/bin/second-brain'

        def read(*args):
            output = subprocess.check_output([str(executable), args[0], str(bundle), *args[1:]],
                                             cwd=root, env=env, text=True)
            return json.loads(output)

        history = read('history', 'garden')
        assert [note['current'] for note in history] == [False, True]
        assert read('list') == history
        assert read('show', 'garden')['body'] == (root / 'examples/inputs/garden-v2.md').read_text()
        assert read('show', 'garden', '--revision', 'r000001')['body'] == (
            root / 'examples/inputs/garden-v1.md').read_text()
        diff = read('diff', 'garden', 'r000001', 'r000002')['diff']
        assert '--- concepts/garden/r000001.md' in diff and '+++ concepts/garden/r000002.md' in diff
        hits = read('search', '물주기')
        assert len(hits) == 2 and all('snippet' in hit for hit in hits)
        current = read('search', '물주기', '--current-only', '--status', 'draft', '--freshness', 'unknown')
        assert len(current) == 1 and current[0]['path'].endswith('r000002.md')
        fresh = read('search', '물주기', '--freshness', 'fresh', '--now', '2026-10-27T00:00:00Z')
        assert len(fresh) == 1 and fresh[0]['path'].endswith('r000001.md')
        print(f'{readme}: install + workflow + revision preservation + browsing/filter assertions: PASS')


def main():
    project = Path(__file__).resolve().parents[1]
    for readme in ('README.md', 'README.ko.md'):
        verify_readme(project, readme)


if __name__ == '__main__':
    main()
