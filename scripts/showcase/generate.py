"""Run from the checkout with its installed Python; all inputs are synthetic.
Usage: .venv/bin/python scripts/showcase/generate.py --logs /outside/checkout/logs
No model is called. Raw outputs stay outside the public site.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / 'scripts/showcase/fixtures'
OUT = ROOT / 'site/data'
NOW = '2026-10-28T00:00:00+00:00'
DEADLINE = '2030-01-01T00:00:00+00:00'


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--logs', type=Path, required=True)
    args = parser.parse_args()
    logs = args.logs.resolve()
    if logs == ROOT or ROOT in logs.parents:
        parser.error('Raw logs must be outside the checkout')
    logs.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    events, frames = [], []
    with tempfile.TemporaryDirectory(prefix='second-brain-showcase-') as tmp:
        bundle = Path(tmp) / 'wiki'

        def run(*argv, frame=False):
            cmd = [sys.executable, '-m', 'local_knowledge_wiki.cli', *map(str, argv)]
            proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
            display = shlex.join(['second-brain', *map(str, argv)]).replace(str(bundle), 'sample/wiki').replace(str(FIX), 'fixtures')
            event = {'command': display, 'stdout': proc.stdout, 'stderr': proc.stderr}
            events.append({'argv': cmd, **event})
            (logs / 'cli-raw.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
            normalized = proc.stdout.replace(str(bundle), 'sample/wiki').replace(str(FIX), 'fixtures')
            if frame:
                frames.append({'command': display, 'output': normalized})
            return json.loads(proc.stdout) if '--format' not in argv else proc.stdout

        run('init', bundle)
        for n in (1, 2):
            run('capture', bundle, FIX / f'report-source-v{n}.txt', '--id', f'report-memo-{n}', '--actor', 'process:showcase', '--resource', f'synthetic:report-memo-{n}')
            run('curate', bundle, 'report-rules', '--body', FIX / f'report-v{n}.md', '--source', f'report-memo-{n}', '--actor', 'prepared-fixture/1', '--title', 'Report-writing rules', '--stale-after', DEADLINE, frame=True)
            if n == 1:
                old_revision = (bundle / 'concepts/report-rules/r000001.md').read_bytes()
                old_source = (bundle / 'sources/report-memo-1/content.raw').read_bytes()
                saved_hashes = {name: hashlib.sha256(value).hexdigest() for name, value in [('revision', old_revision), ('source', old_source)]}
                (logs / 'first-revision-sha256.json').write_text(json.dumps(saved_hashes, indent=2))
            else:
                assert (bundle / 'concepts/report-rules/r000001.md').read_bytes() == old_revision
                assert (bundle / 'sources/report-memo-1/content.raw').read_bytes() == old_source
        run('capture', bundle, FIX / 'research-source.txt', '--id', 'research-memo', '--actor', 'process:showcase', '--resource', 'synthetic:research-memo')
        run('curate', bundle, 'research-handoff', '--body', FIX / 'research.md', '--source', 'research-memo', '--actor', 'prepared-fixture/1', '--title', 'Research handoff', '--stale-after', DEADLINE)
        search = run('search', bundle, 'report', '--current-only', '--now', NOW)
        run('search', bundle, 'report', '--current-only', '--now', NOW, '--format', 'text', frame=True)
        run('show', bundle, 'report-rules', '--now', NOW, '--format', 'text', frame=True)
        notes = []
        for id_, ko in [('report-rules', '보고서 작성 규칙'), ('research-handoff', '조사 자료 전달')]:
            history = run('history', bundle, id_, '--now', NOW)
            revisions = [run('show', bundle, id_, '--revision', item['path'].split('/')[-1][:-3], '--now', NOW) for item in history]
            current = run('show', bundle, id_, '--now', NOW)
            assert current['current'] and current['path'] in (bundle / 'index.md').read_text()
            sources = {}
            for rev in revisions:
                for source in rev['metadata']['sources']:
                    raw = (bundle / 'sources' / source['id'] / 'content.raw').read_bytes()
                    expected = FIX / ({'report-memo-1': 'report-source-v1.txt', 'report-memo-2': 'report-source-v2.txt', 'research-memo': 'research-source.txt'}[source['id']])
                    assert raw == expected.read_bytes()
                    sources[source['id']] = {'text': raw.decode(), 'sha256': hashlib.sha256(raw).hexdigest()}
            diff = run('diff', bundle, id_, 'r000001', f'r{len(revisions):06}', '--now', NOW)
            notes.append({'id': id_, 'titleKo': ko, 'revisions': revisions, 'sources': sources, 'diff': diff['diff']})
        assert notes[0]['revisions'][0]['body'] == (FIX / 'report-v1.md').read_text()
        assert notes[0]['revisions'][1]['body'] == (FIX / 'report-v2.md').read_text()
        run('diff', bundle, 'report-rules', 'r000001', 'r000002', '--now', NOW, '--format', 'text', frame=True)
        check = run('check', bundle, '--now', NOW)
        assert check['invalid'] == [] and check['warnings'] == [] and check['stale'] == []
        assert search[0]['current'] is True and search[0]['path'].endswith('r000002.md')
        data = {'evaluatedAt': NOW, 'deadline': DEADLINE, 'notes': notes, 'search': search, 'check': check, 'frames': frames, 'preservedSha256': saved_hashes}
        (OUT / 'sample.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        transcript = 'Synthetic prepared text; no model generation. Actual CLI output.\nTiming edited for replay; temporary bundle path normalized to sample/wiki.\n\n'
        transcript += '\n\n'.join('$ ' + f['command'] + '\n' + f['output'] for f in frames)
        (OUT / 'transcript.txt').write_text(transcript)
        (logs / 'assertions.txt').write_text('PASS: exact captured source bytes, full earlier revision/source bytes unchanged after update, earlier/current body bytes, index current selection, exact-word search and clean check.\n')
        print('Generated sample.json and transcript.txt from actual CLI results; assertions passed.')


if __name__ == '__main__':
    main()
