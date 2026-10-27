"""Run the README shell blocks in a fresh, disposable project copy."""

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
        env = {**os.environ, 'TMPDIR': str(tmp), 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
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
        print(f'{readme}: install + full workflow + revision preservation: PASS')


def main():
    project = Path(__file__).resolve().parents[1]
    for readme in ('README.md', 'README.ko.md'):
        verify_readme(project, readme)


if __name__ == '__main__':
    main()
