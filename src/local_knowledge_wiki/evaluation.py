"""Explicit judgments against one bounded current corpus and delivered recall output."""

import json
import re
from collections import Counter
from datetime import datetime, timezone

from .annotations import canonical_time, fields, local_id, text
from .context import NOTE_LIMIT, READ_BYTES
from .errors import WikiError, error_code
from .graph import pack
from .limits import file_limit
from .reading import REVISION_PATH, read_note
from .recall import recall_request, recall_result, words
from .requests import digest, encoded
from .storage import Store, current_index, read_input


CASE_BYTES = 2097152
MODES = tuple(f'{match}:{rank}' for match in ('auto', 'exact', 'lexical') for rank in ('frequency', 'bm25'))


def cases_file(path):
    raw = read_input(path, max_bytes=CASE_BYTES)
    def pairs(items):
        value = {}
        for key, child in items:
            if key in value:
                raise WikiError('Duplicate evaluation JSON key')
            value[key] = child
        return value
    def constant(_):
        raise WikiError('Nonfinite evaluation JSON value')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
        stack = [(value, 0)]; visited = 0
        while stack:
            item, depth = stack.pop(); visited += 1
            if depth > 8 or visited > 50000:
                raise WikiError('Evaluation depth/value limit exceeded', 'input_too_large')
            if isinstance(item, dict):
                stack.extend((child, depth + 1) for pair in item.items() for child in pair)
            elif isinstance(item, list): stack.extend((v, depth + 1) for v in item)
        fields(value, ('version', 'target_mode', 'cases'))
        if type(value['version']) is not int or value['version'] != 1 or value['target_mode'] not in ('current_id', 'exact_revision'):
            raise WikiError('Unsupported evaluation version/target mode')
        if not isinstance(value['cases'], list) or not 1 <= len(value['cases']) <= 100:
            raise WikiError('Evaluation needs 1..100 explicit cases')
        ids = set()
        for case in value['cases']:
            fields(case, ('id', 'query', 'gold'), ('expect_no_match',))
            local_id(case['id']); text(case['query'], 'case query', 65536)
            if not words(case['query']) or case['id'] in ids:
                raise WikiError('Duplicate case ID or query without words')
            ids.add(case['id'])
            if not isinstance(case['gold'], list) or len(case['gold']) > 32:
                raise WikiError('Gold must contain at most 32 distinct targets')
            if 'expect_no_match' in case and type(case['expect_no_match']) is not bool:
                raise WikiError('expect_no_match must be boolean')
            if (not case['gold']) != case.get('expect_no_match', False):
                raise WikiError('Only empty gold controls require expect_no_match=true')
            targets = set()
            for target in case['gold']:
                fields(target, ('id',) if value['target_mode'] == 'current_id' else ('id', 'revision'),
                       () if value['target_mode'] == 'current_id' else ('sha256',))
                local_id(target['id'])
                if 'revision' in target and (not isinstance(target['revision'], str) or not re.fullmatch(r'r(?!000000)[0-9]{6}', target['revision'])):
                    raise WikiError('Invalid gold revision')
                if 'sha256' in target and (not isinstance(target['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', target['sha256'])):
                    raise WikiError('Invalid gold digest')
                identity = (target['id'], target.get('revision'))
                if identity in targets:
                    raise WikiError('Duplicate gold target')
                targets.add(identity)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise WikiError('Invalid strict evaluation case JSON') from exc
    return raw, value


class FrozenNote:
    def __init__(self, raw): self.raw = raw
    def read(self, path): return self.raw


def evaluate(root, cases, scope=None, mode=None, k=None, result_max_chars=12000, max_chars=12000, now=None):
    if type(max_chars) is not int or not 2048 <= max_chars <= 1000000 or type(result_max_chars) is not int or not 2048 <= result_max_chars <= 1000000:
        raise WikiError('Output budgets must be 2048..1000000')
    modes = list(dict.fromkeys(mode if mode is not None else ['auto:frequency']))
    ks = sorted(set(k if k is not None else [1, 3, 5, 10]))
    if not modes or len(modes) > 6 or any(m not in MODES for m in modes) or not ks or any(type(n) is not int or not 1 <= n <= 100 for n in ks):
        raise WikiError('Invalid evaluation modes or k values')
    at = canonical_time(now if now is not None else datetime.now(timezone.utc)); instant = datetime.fromisoformat(at)
    raw_cases, judgments = cases_file(cases)
    ids = sorted(set(scope or []))
    for ident in ids: local_id(ident)
    scan = {'selected': 0, 'processed': 0, 'read_bytes': 0, 'budget_charged_bytes': 0, 'complete': True,
            'limits': {'notes': NOTE_LIMIT, 'note_bytes': READ_BYTES}}
    notes, hashes, diagnostics = [], {}, []
    excluded = {'unavailable': 0, 'unsupported_revision': 0, 'invalid_utf8': 0}
    invalid_metadata = 0
    with Store(root) as store:
        try:
            before = store.read('index.md'); all_current = current_index(before.decode('utf-8'))[0]
        except (OSError, WikiError, UnicodeError) as exc:
            raise WikiError('Evaluation requires a valid readable current index', 'invalid_index') from exc
        if scope is not None and any(ident not in all_current for ident in ids):
            raise WikiError('Requested evaluation ID is not indexed', 'not_found')
        current = {ident: all_current[ident] for ident in ids} if scope is not None else all_current
        scan['selected'] = len(current)
        for path in sorted(current.values()):
            remaining = READ_BYTES - scan['budget_charged_bytes']
            if scan['processed'] >= NOTE_LIMIT or remaining <= 0:
                scan['complete'] = False
                diagnostics.append({'path': None, 'kind': 'scan_limit'})
                break
            scan['processed'] += 1
            identity = REVISION_PATH.fullmatch(path)
            if not identity or identity[2] == 'r000000':
                excluded['unsupported_revision'] += 1; scan['complete'] = False
                diagnostics.append({'path': path, 'kind': 'unsupported_revision'})
                continue
            try:
                raw = store.read(path, budget_bytes=remaining)
            except (OSError, WikiError) as exc:
                scan['budget_charged_bytes'] += min(file_limit(path), remaining)
                scan['read_bytes'] = None; scan['complete'] = False; excluded['unavailable'] += 1
                diagnostics.append({'path': path, 'kind': 'unavailable', 'code': error_code(exc)})
                continue
            scan['budget_charged_bytes'] += len(raw)
            if scan['read_bytes'] is not None: scan['read_bytes'] += len(raw)
            hashes[path] = digest(raw)
            try:
                note, _ = read_note(FrozenNote(raw), path, instant, current)
                if note['metadata_errors'] == ['Note must be UTF-8']:
                    excluded['invalid_utf8'] += 1; scan['complete'] = False
                    diagnostics.append({'path': path, 'kind': 'invalid_utf8'})
                    continue
                if note['metadata_errors']: invalid_metadata += 1
                counts = Counter(words((note['title'] if isinstance(note['title'], str) else '') + '\n' + note['body']))
                notes.append((identity, note, counts))
            except (WikiError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
                scan['complete'] = False; excluded['unavailable'] += 1
                diagnostics.append({'path': path, 'kind': 'unavailable', 'code': error_code(exc)})
        try:
            final_index = store.read('index.md')
            changed = final_index != before
            final_digest = digest(final_index)
        except (OSError, WikiError):
            changed = True
            final_digest = None
    if changed:
        scan['complete'] = False; diagnostics.append({'path': 'index.md', 'kind': 'index_changed'})
    rows, aggregates = [], {m: [] for m in modes}
    available = {note['path'] for _, note, _ in notes}
    complete = scan['complete']; failures = 0
    comparisons = {m: {'improved': 0, 'regressed': 0, 'unchanged': 0, 'unscorable': 0} for m in modes[1:]}
    for case in judgments['cases']:
        gold, errors = [], []
        for target in case['gold']:
            ident = target['id']; path = current.get(ident)
            reason = ('gold_out_of_scope' if ident in all_current and ident not in current else 'gold_not_indexed' if path is None else
                      'gold_not_current' if 'revision' in target and path != f"concepts/{ident}/{target['revision']}.md" else
                      'gold_unavailable' if path not in available else
                      'gold_hash_mismatch' if 'sha256' in target and hashes.get(path) != target['sha256'] else None)
            if reason: errors.append({'id': ident, 'reason': reason})
            else: gold.append(path)
        row = {'id': case['id'], 'query': case['query'], 'gold': case['gold'], 'errors': errors, 'modes': {}}
        if errors: complete = False
        for method in modes:
            match, rank = method.split(':')
            try:
                terms, result = recall_request(case['query'], match, max(ks), result_max_chars, rank)
                result.update(indexed=len(current), excluded=dict(excluded), invalid_metadata_notes=invalid_metadata)
                result = recall_result(result, current, notes, terms, match, max(ks), result_max_chars, rank)
                delivered = [item['path'] for item in result['results']]
                ranks = {path: delivered.index(path) + 1 for path in gold if path in delivered}
                valid = scan['complete'] and not errors
                metric = {'recall_at': {str(n): sum(r <= n for r in ranks.values()) / len(gold) for n in ks},
                          'mrr_at_k': 1 / min(ranks.values()) if ranks else 0.0} if valid and gold else None
                row['modes'][method] = {'state': result['state'], 'match_mode': result['match_mode'],
                    'fallback_used': result['fallback_used'], 'delivered': delivered, 'ranks': ranks,
                    'missing_gold': [path for path in gold if path not in ranks], 'metrics': metric,
                    'excluded': result['excluded'], 'omitted_results': result['omitted_results'],
                    'result_count_budget_limited': len(delivered) < min(max(ks), result['matched']),
                    'no_match_passed': result['matched'] == 0 if valid and case.get('expect_no_match') else None,
                    'reason': 'invalid_label' if errors else 'corpus_incomplete' if not scan['complete'] else
                              'budget_omitted' if len(delivered) < min(max(ks), result['matched']) else
                              'no_match' if not result['matched'] else 'gold_not_delivered' if len(ranks) < len(gold) else None}
            except Exception as exc:
                complete = False; failures += 1
                row['modes'][method] = {'metrics': None, 'no_match_passed': None, 'reason': 'case_failure', 'code': error_code(exc)}
            aggregates[method].append(row['modes'][method])
        row['comparisons_to_first'] = {}
        baseline = row['modes'][modes[0]]['metrics']
        for method in modes[1:]:
            other = row['modes'][method]['metrics']
            if baseline is None or other is None: key = 'unscorable'
            else:
                a = (baseline['recall_at'][str(max(ks))], baseline['mrr_at_k'])
                b = (other['recall_at'][str(max(ks))], other['mrr_at_k'])
                key = 'improved' if b > a else 'regressed' if b < a else 'unchanged'
            comparisons[method][key] += 1
            row['comparisons_to_first'][method] = key
        rows.append(row)
    summaries = []
    for method in modes:
        metrics = [r['metrics'] for r in aggregates[method] if r['metrics'] is not None]
        controls = [r['no_match_passed'] for r in aggregates[method] if r['no_match_passed'] is not None]
        summaries.append({'mode': method, 'metrics': {'recall_at': {str(n): sum(m['recall_at'][str(n)] for m in metrics) / len(metrics) for n in ks},
                          'mrr_at_k': sum(m['mrr_at_k'] for m in metrics) / len(metrics)} if complete and metrics else None,
                          'judged_cases': len(metrics), 'no_match_controls': len(controls),
                          'no_match_accuracy': sum(controls) / len(controls) if complete and controls else None,
                          'comparison_to_first': comparisons.get(method)})
    report = {'schema_version': 1, 'command': 'eval-retrieval', 'evaluated_at': at,
        'scope': {'selection': 'indexed-current', 'requested_count': len(ids) if scope is not None else None,
                  'requested_sha256': digest(encoded(ids)) if scope is not None else None},
        'identity': {'cases_sha256': digest(raw_cases), 'index_sha256': digest(before), 'final_index_sha256': final_digest,
                     'manifest_sha256': digest(encoded(sorted(hashes.items())))},
        'target_mode': judgments['target_mode'], 'consistency': 'best_effort_frozen_read_set', 'index_changed': changed,
        'scan': scan, 'analysis_complete': complete, 'output_complete': True, 'partial': False,
        'horizon_k': max(ks), 'result_max_chars': result_max_chars,
        'counts': {'cases': len(rows), 'modes': len(modes), 'invalid_labels': sum(bool(r['errors']) for r in rows), 'case_failures': failures},
        'guidance': 'Explicit judgments, not generated truth. Metrics measure delivered output; incomplete corpus or labels null primary aggregates.',
        'omitted': {'diagnostics': max(0, len(diagnostics) - 1000), 'summaries': 0, 'cases': 0}, 'diagnostics': [], 'summaries': [], 'cases': []}
    return pack(report, {'summaries': summaries, 'diagnostics': diagnostics[:1000], 'cases': rows}, max_chars)
