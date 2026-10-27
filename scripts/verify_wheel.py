"""Build and smoke-test a wheel: python scripts/verify_wheel.py (requires pip)."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    project = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='second-brain-wheel-') as temporary:
        root = Path(temporary).resolve()
        home = root / 'home'
        home.mkdir()
        env = {key: value for key, value in os.environ.items() if not key.startswith('PYTHON')}
        env.update(HOME=str(home), PYTHONPATH='', PYTHONNOUSERSITE='1',
                   PIP_CACHE_DIR=str(root / 'pip-cache'), PIP_DISABLE_PIP_VERSION_CHECK='1',
                   PIP_CONFIG_FILE=os.devnull)

        def run(*args):
            return subprocess.run(list(map(str, args)), cwd=root, env=env, check=True,
                                  text=True, encoding='utf-8', stdout=subprocess.PIPE).stdout

        wheels = root / 'wheels'
        print(run(sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--wheel-dir', wheels,
                  project), end='')
        wheel, = wheels.glob('local_second_brain-*.whl')
        isolated = root / 'venv'
        run(sys.executable, '-m', 'venv', isolated)
        python = isolated / 'bin/python'
        print(run(python, '-m', 'pip', 'install', wheel), end='')
        print(run(python, '-m', 'pip', 'check'), end='')
        # This fixed code checks the installed import, not any captured input.
        print(run(python, '-I', '-c', '''
import json, sys, sysconfig
from pathlib import Path
import local_knowledge_wiki
prefix = Path(sys.prefix).resolve()
package = Path(local_knowledge_wiki.__file__).resolve()
assert prefix == Path(sys.argv[1]).resolve(), (prefix, sys.argv[1])
assert sys.prefix != sys.base_prefix
assert package.is_relative_to(Path(sysconfig.get_path('purelib')).resolve()), package
assert package.is_relative_to(prefix), package
assert not package.is_relative_to(Path(sys.argv[2]).resolve()), package
print(json.dumps({'installed_package': str(package), 'venv': str(prefix)}))
''', isolated, project), end='')

        executable = isolated / 'bin/second-brain'
        bundle = root / 'wiki'

        def cli(command, *args):
            return json.loads(run(executable, command, bundle, *args))

        def snapshot():
            return {p.relative_to(bundle): p.read_bytes()
                    for p in bundle.rglob('*') if p.is_file()}

        source = root / 'synthetic source.raw'
        source_bytes = b'\xef\xbb\xbfSynthetic lantern record\r\n\xff\x00'
        source.write_bytes(source_bytes)
        body = root / 'synthetic body.md'
        first_body = '# Synthetic lantern\n\nUse amber trays. 달빛\n'
        body.write_text(first_body, encoding='utf-8')
        cli('init')
        cli('capture', source, '--id', 'note', '--actor', 'process:wheel-smoke',
            '--resource', 'synthetic:wheel-smoke')
        raw = bundle / 'sources/note/content.raw'
        provenance = raw.with_name('provenance.json')
        assert raw.read_bytes() == source_bytes
        assert json.loads(provenance.read_text())['sha256'] == hashlib.sha256(source_bytes).hexdigest()
        curate_args = ('lantern', '--body', body, '--source', 'note', '--actor', 'smoke/1',
                       '--title', 'Synthetic lantern 달빛')
        assert cli('curate', *curate_args)['revision'] == 'concepts/lantern/r000001.md'
        first = bundle / 'concepts/lantern/r000001.md'
        preserved = {p: p.read_bytes() for p in (raw, provenance, first)}
        reviewed = cli('review', 'lantern', '--revision', 'r000001',
                       '--actor', 'process:wheel-smoke', '--evidence', 'sources/note/content.raw')
        assert reviewed['revision'] == 'concepts/lantern/r000002.md'
        event = reviewed['verified'][0]
        assert event['x-second-brain-target']['sha256'] == hashlib.sha256(preserved[first]).hexdigest()
        assert event['x-second-brain-evidence']['sha256'] == hashlib.sha256(source_bytes).hexdigest()
        note = cli('show', 'lantern')
        assert note['body'] == first_body and note['trust'] == 'machine-confirmed'
        second = bundle / reviewed['revision']
        preserved[second] = second.read_bytes()
        final_body = '# Synthetic lantern\n\nUse cobalt trays. 달빛\n'
        body.write_text(final_body, encoding='utf-8')
        assert cli('curate', *curate_args)['revision'] == 'concepts/lantern/r000003.md'
        assert all(p.read_bytes() == data for p, data in preserved.items())

        before = snapshot()
        current = cli('show', 'lantern')
        assert current['body'] == final_body and current['trust'] == 'unverified'
        assert 'verified' not in current['metadata']
        assert cli('show', 'lantern', '--revision', 'r000001')['body'] == first_body
        history = cli('history', 'lantern')
        assert [n['current'] for n in history] == [False, False, True]
        assert cli('list') == history
        hits = cli('search', '달빛', '--current-only')
        assert len(hits) == 1 and hits[0]['path'] == current['path']
        assert len(cli('search', 'lantern')) == 3
        diff = cli('diff', 'lantern', 'r000001', 'r000003')['diff']
        assert '-Use amber trays.' in diff and '+Use cobalt trays.' in diff
        assert cli('check') == {'invalid': [], 'warnings': [], 'stale': [], 'concepts': 3}
        for command, args in (('list', ()), ('show', ('lantern',)),
                              ('history', ('lantern',)),
                              ('diff', ('lantern', 'r000001', 'r000003')),
                              ('search', ('달빛',))):
            assert '달빛' in run(executable, command, bundle, *args, '--format', 'text')
        assert snapshot() == before, 'Read commands changed bundle artifacts'
        assert not (bundle / '.lkw.lock').exists()
        print('Wheel smoke: isolated import + CLI workflow + review + reads + byte preservation: PASS')


if __name__ == '__main__':
    main()
