"""Synthetic quality and startup-inclusive scale study; no generated corpus is retained.

Run with the project Python and PYTHONPATH pointing to this checkout's src.
Outputs JSON to stdout. --profile writes an optional separate untimed cProfile file.
"""

import argparse
import cProfile
import importlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from local_knowledge_wiki.recall import recall
from local_knowledge_wiki.storage import END, START, render_entries


NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/recall-ranking.json'


def corpus(root, notes):
    entries = {}
    for note in notes:
        folder = root / 'concepts' / note['id']
        folder.mkdir(parents=True)
        body = note['body'] * note.get('repeat', 1) + note.get('suffix', '')
        for revision in (1, 2, 3):
            text = body if revision == 2 else note.get('history', 'historical superseded unrelated report evidence')
            metadata = json.dumps({'type': 'Concept', 'title': note['title'], 'status': 'draft'}, ensure_ascii=False)
            (folder / f'r{revision:06}.md').write_text('---\n' + metadata + '\n---\n' + text, encoding='utf-8')
        entries[note['id']] = f"concepts/{note['id']}/r000002.md"
    (root / 'index.md').write_text(START + render_entries(entries) + END + '\n', encoding='utf-8')
    return {'current_notes': len(notes), 'revisions': len(notes) * 3,
            'stored_bytes': sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
            'current_bytes': sum((root / path).stat().st_size for path in entries.values())}


def no_title_scores(notes, terms, mode, term_counts):
    # Ablation only: the production BM25-v1 formula with the title hint removed.
    size = len(notes)
    average = sum(sum(counts.values()) for _, _, counts in notes) / size if size else 1
    average = average or 1
    weights = [math.log1p((size - sum(c[i] > 0 for c in term_counts) + .5)
                         / (sum(c[i] > 0 for c in term_counts) + .5)) for i in range(len(terms))]
    return [sum(w * count * 2.2 / (count + 1.2 * (.25 + .75 * sum(counts.values()) / average))
                for count, w in zip(occurrences, weights) if count)
            for (_, _, counts), occurrences in zip(notes, term_counts)]


def quality(root):
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
    info = corpus(root, fixture['notes'])
    rows = []
    module = importlib.import_module('local_knowledge_wiki.recall')
    for case in fixture['queries']:
        row = dict(case, variants={})
        candidates = None
        for method in ('frequency', 'bm25-no-title', 'bm25'):
            with patch.object(module, 'bm25_scores', no_title_scores if method == 'bm25-no-title' else module.bm25_scores):
                result = recall(root, case['query'], NOW, case.get('match', 'auto'), 100, 1000000,
                                'frequency' if method == 'frequency' else 'bm25')
            assert result['indexed'] == info['current_notes'] and not any(result['excluded'].values()), result
            assert result['omitted_results'] == 0 and result['state'] in ('matches', 'no_match'), result
            ranking = [item['id'] for item in result['results']]
            assert all(item['revision'] == 'r000002' for item in result['results'])
            if candidates is None:
                candidates = set(ranking)
            assert candidates == set(ranking), row
            rank = ranking.index(case['expected']) + 1 if case['expected'] in ranking else None
            row['variants'][method] = {'ranking': ranking, 'rank': rank,
                                       'match_mode': result['match_mode'], 'fallback_used': result['fallback_used']}
        rows.append(row)
    judged = [row for row in rows if row['expected'] is not None]
    metrics = {method: {'queries': len(judged),
                        'top1': sum(row['variants'][method]['rank'] == 1 for row in judged) / len(judged),
                        'mrr': sum(1 / row['variants'][method]['rank'] if row['variants'][method]['rank'] else 0
                                   for row in judged) / len(judged)}
               for method in ('frequency', 'bm25-no-title', 'bm25')}
    return {'description': fixture['description'], 'corpus': info, 'metrics': metrics, 'queries': rows}


def measure(root, method):
    command = [sys.executable, '-m', 'local_knowledge_wiki.cli',
               'search' if method == 'search' else 'recall', str(root), 'report evidence']
    if method != 'search':
        command += ['--rank', method]
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        start = time.perf_counter()
        child = subprocess.Popen(command, stdout=out, stderr=err)
        rss = None
        if hasattr(os, 'wait4') and sys.platform in ('darwin', 'linux'):
            _, status, usage = os.wait4(child.pid, 0)
            child.returncode = os.waitstatus_to_exitcode(status)
            rss = usage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
        else:
            child.wait()
        elapsed = time.perf_counter() - start
        out.seek(0)
        err.seek(0)
        raw = out.read()
        text = raw.decode('utf-8')
        assert child.returncode == 0, (command, err.read())
        result = json.loads(text)
        if method == 'search':
            assert isinstance(result, list) and result, result
            assert {item['path'].split('/')[-1] for item in result} == {'r000001.md', 'r000002.md', 'r000003.md'}
            summary = {'results': len(result), 'top_path': result[0]['path']}
        else:
            assert result['state'] == 'matches' and result['indexed'] == result['matched'], result
            assert not any(result['excluded'].values()) and result['results'], result
            assert all(item['revision'] == 'r000002' for item in result['results']), result
            assert len(text) <= result['max_chars'], len(text)
            summary = {'indexed': result['indexed'], 'matched': result['matched'],
                       'results': len(result['results']), 'top_path': result['results'][0]['path']}
    return {'seconds': elapsed, 'peak_rss_bytes': rss, **summary,
            'stdout_codepoints': len(text), 'stdout_bytes': len(raw), 'returncode': child.returncode}



def scale(root, sizes, runs, profile_path):
    output = []
    for size in sizes:
        folder = root / str(size)
        folder.mkdir()
        notes = [{'id': f'n{i:05}', 'title': 'Report evidence' if i == 0 else 'Synthetic log',
                  'body': 'report evidence ' + 'filler ' * ([12, 80, 400, 1600][i % 4] if i % 50 else 5000)}
                 for i in range(size)]
        info = corpus(folder, notes)
        samples = {'frequency': [], 'bm25': [], 'search': []}
        for run in range(runs + 1):
            for method in (('frequency', 'bm25', 'search') if run % 2 == 0 else ('search', 'bm25', 'frequency')):
                sample = measure(folder, method)
                assert sample['results'] == size * 3 if method == 'search' else sample['indexed'] == size
                samples[method].append(sample)
        summaries = {}
        for method, measurements in samples.items():
            subsequent = [sample['seconds'] for sample in measurements[1:]]
            summaries[method] = {'first': measurements[0], 'subsequent': measurements[1:],
                                 'subsequent_seconds_median': statistics.median(subsequent),
                                 'subsequent_seconds_min': min(subsequent),
                                 'subsequent_seconds_max': max(subsequent)}
        output.append({'corpus': info, 'methods': summaries})
        if profile_path and size == max(sizes):
            profiler = cProfile.Profile()
            profiler.runcall(recall, folder, 'report evidence', NOW, rank='bm25')
            profiler.dump_stats(profile_path)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', type=int, nargs='+', default=[10, 100, 1000])
    parser.add_argument('--runs', type=int, default=5, help='Subsequent subprocesses per method after first run')
    parser.add_argument('--profile', help='Optional separate untimed profile output, outside generated corpus')
    args = parser.parse_args()
    if args.runs < 1 or any(size < 1 for size in args.sizes):
        parser.error('positive sizes and runs required')
    with tempfile.TemporaryDirectory(prefix='recall-benchmark-') as temporary:
        root = Path(temporary)
        quality_root = root / 'quality'
        quality_root.mkdir()
        result = {'environment': {'python': sys.version, 'executable': sys.executable,
                                  'platform': platform.platform(), 'cpu_count': os.cpu_count(),
                                  'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None},
                  'measurement': {'wall': 'CLI subprocess startup through exit; parsing/validation outside timed region',
                                  'cache': 'uncontrolled; first run is not cold', 'subsequent_runs': args.runs,
                                  'rss': 'per-child wait4 ru_maxrss, normalized to bytes (Darwin bytes; Linux KiB); null otherwise',
                                  'ordering': 'alternate frequency/BM25/search then reverse each round; no speedup claim',
                                  'contracts': 'recall scans indexed current only and bounds stdout; unchanged search spans all revisions with unbounded stdout'},
                  'quality': quality(quality_root),
                  'scale': scale(root, args.sizes, args.runs, args.profile)}
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
