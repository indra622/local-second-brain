#!/usr/bin/env python3
"""Deterministic synthetic CLI orchestration; no model or factual verification."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


FIXTURES = Path(__file__).resolve().parent / 'reuse-inputs'
ACTOR = 'process:synthetic-demo'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run_demo(output):
    output = Path(output).absolute()
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError('Output must be a new or empty directory, not a symlink')
    output.mkdir(parents=True, exist_ok=True)
    bundle = output / 'wiki'
    prepared = output / 'prepared'
    prepared.mkdir()
    events = []

    def cli(command, *args):
        arguments = [command, str(bundle), *map(str, args)]
        result = subprocess.run([sys.executable, '-m', 'local_knowledge_wiki.cli', *arguments],
                                capture_output=True, text=True, encoding='utf-8', timeout=30)
        require(result.returncode == 0, result.stderr or result.stdout)
        data = json.loads(result.stdout)
        events.append({'arguments': arguments, 'result': data})
        return data

    def save(name, data):
        with (output / name).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    def capture(version):
        cli('capture', FIXTURES / f'source-{version}.txt', '--id', f'lantern-{version}',
            '--actor', ACTOR, '--resource', f'synthetic:lantern-{version}')

    def curate(version):
        body = prepared / f'body-{version}.md'
        with body.open('xb') as stream:
            stream.write((FIXTURES / f'body-{version}.md').read_bytes())
        cli('curate', 'lantern', '--body', body, '--source', f'lantern-{version}',
            '--actor', ACTOR, '--title', 'Synthetic lantern rehearsal')

    cli('init')
    empty = cli('search', 'lantern', '--current-only')
    require(empty == [], 'Initial lookup must be empty')
    capture('v1')
    curate('v1')
    first = cli('show', 'lantern')
    require(first['body'] == (FIXTURES / 'body-v1.md').read_text(encoding='utf-8'),
            'Prepared v1 body must be stored intact')
    require(first['trust'] == 'unverified', 'Writing must not record review')
    original = {path.relative_to(bundle): path.read_bytes()
                for path in bundle.rglob('*') if path.is_file() and path.name != 'index.md'}

    # This process declares a demo comparison, never a human or authenticated review.
    require('amber trays' in first['body'] and 'two bells' in first['body'], 'Unexpected v1 plan')
    cli('review', 'lantern', '--revision', 'r000001', '--actor', ACTOR,
        '--evidence', 'sources/lantern-v1/content.raw')
    reviewed = cli('show', 'lantern')
    require(reviewed['body'] == first['body'] and reviewed['trust'] == 'machine-confirmed',
            'Demo review must preserve the body and use a process declaration')
    original[Path(reviewed['path'])] = (bundle / reviewed['path']).read_bytes()

    def reuse(stage, expected, revision):
        hits = cli('search', 'lantern', '--current-only')
        require(len(hits) == 1 and hits[0]['path'].endswith(revision + '.md'),
                'Recall must select only the indexed current revision')
        note = cli('show', 'lantern')
        require(note['current'] is True and note['path'] == hits[0]['path'], 'Search/show disagree')
        require(expected in note['body'], 'Later task must reuse the expected plan')
        artifact = {'task': 'Prepare a fictional rehearsal checklist from recalled knowledge',
                    'method': 'Deterministic body copy, not LLM synthesis',
                    'reused_revision': note['path'], 'trust': note['trust'],
                    'body': note['body']}
        save(f'reuse-{stage}.json', artifact)
        return artifact

    before = reuse('before', 'amber trays and two bells', 'r000002')
    capture('v2')
    curate('v2')
    after = reuse('after', 'cobalt trays and three bells', 'r000003')
    current = cli('show', 'lantern')
    require(current['body'] == (FIXTURES / 'body-v2.md').read_text(encoding='utf-8'), 'V2 body changed')
    require(current['trust'] == 'unverified' and 'verified' not in current['metadata'],
            'Content edit must not inherit the demo review')
    require(before['body'] != after['body'], 'Later task must reflect revised knowledge')
    history = cli('history', 'lantern')
    require([note['current'] for note in history] == [False, False, True], 'Unexpected history')
    difference = cli('diff', 'lantern', 'r000001', 'r000003')
    require('-Use amber trays and two bells' in difference['diff']
            and '+Use cobalt trays and three bells' in difference['diff'], 'Missing body comparison')
    for version in ('v1', 'v2'):
        source = bundle / f'sources/lantern-{version}/content.raw'
        require(source.read_bytes() == (FIXTURES / f'source-{version}.txt').read_bytes(),
                'Captured source bytes changed')
        provenance = json.loads(source.with_name('provenance.json').read_text(encoding='utf-8'))
        require(provenance['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest(),
                'Source digest mismatch')
    require(all((bundle / path).read_bytes() == data for path, data in original.items()),
            'Previous source, provenance or revision bytes changed')
    report = cli('check')
    require(report == {'invalid': [], 'warnings': [], 'stale': [], 'concepts': 3},
            'Unexpected final format/link report')
    save('transcript.json', events)
    summary = {'output': str(output), 'bundle': str(bundle), 'initial_hits': len(empty),
               'revisions': len(history), 'current': current['path'], 'trust': current['trust'],
               'preserved_files': len(original), 'check': report,
               'limitations': 'Prewritten synthetic notes; no LLM, product integration or factual verification. '
                              'process:synthetic-demo is an unauthenticated demo declaration. '
                              'CLI timestamps and output paths vary between runs.'}
    save('summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New or empty output directory; default: retained temp directory')
    args = parser.parse_args()
    try:
        output = args.output if args.output is not None else Path(tempfile.mkdtemp(prefix='second-brain-reuse-'))
        print(json.dumps(run_demo(output), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'knowledge-reuse: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
