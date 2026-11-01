"""Read-only observations and source-byte checks, never factual verification."""

import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone

from . import annotations
from .errors import WikiError, error_code
from .format import timestamp
from .graph import _graph, pack
from .limits import METADATA_BYTES, SOURCE_BYTES
from .requests import digest, encoded
from .storage import Store, identifier, single_line


VERIFY_BYTES = 134217728
FINDING_LIMIT = 10000


def provenance(raw, source_id):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise WikiError('Duplicate provenance JSON key')
            result[key] = value
        return result
    def constant(_):
        raise WikiError('Nonfinite provenance value')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    annotations.fields(value, ('id', 'original_name', 'resource', 'captured', 'sha256', 'bytes'))
    annotations.fields(value['captured'], ('by', 'at'))
    if value['id'] != source_id or not isinstance(value['original_name'], str) or not value['original_name']:
        raise WikiError('Invalid captured source identity')
    if not isinstance(value['resource'], str):
        raise WikiError('Provenance resource must be a string locator')
    single_line(value['captured']['by'], 'captured.by')
    timestamp(value['captured']['at'])
    if type(value['bytes']) is not int or not 0 <= value['bytes'] <= SOURCE_BYTES:
        raise WikiError('Invalid provenance byte count')
    if not isinstance(value['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', value['sha256']):
        raise WikiError('Invalid provenance digest')
    return value


def verify(store, source_id, io):
    def read(path, limit, collect=False):
        with store.parent(path) as (fd, name):
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(handle, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise WikiError('Source check requires regular files', 'unsafe_path')
                if info.st_size > VERIFY_BYTES - io['bytes_read']:
                    return None, None, 'unchecked_budget'
                if info.st_size > limit:
                    return None, None, 'unchecked_limit'
                data = bytearray() if collect else None
                value = hashlib.sha256()
                used = 0
                while True:
                    remaining = VERIFY_BYTES - io['bytes_read']
                    if remaining <= 0:
                        if os.fstat(stream.fileno()).st_size != used:
                            return None, used, 'unchecked_budget'
                        break
                    block = stream.read(min(65536, remaining, limit - used + 1))
                    if not block:
                        break
                    io['bytes_read'] += len(block)
                    used += len(block)
                    if used > limit:
                        return None, used, 'unchecked_limit'
                    value.update(block)
                    if collect:
                        data.extend(block)
                return bytes(data) if collect else value.hexdigest(), used, None
    result = {'source_id': source_id, 'state': 'unchecked'}
    try:
        raw, _, state = read(f'sources/{source_id}/provenance.json', METADATA_BYTES, True)
        if state:
            result['state'] = state
            return result
        try:
            declared = provenance(raw, source_id)
        except (WikiError, UnicodeError, ValueError, TypeError, KeyError, RecursionError):
            result['state'] = 'invalid_provenance'
            return result
        observed, used, state = read(f'sources/{source_id}/content.raw', SOURCE_BYTES)
        result.update(state=state or ('matched' if observed == declared['sha256'] and used == declared['bytes'] else 'hash_mismatch'),
                      expected_sha256=declared['sha256'], expected_bytes=declared['bytes'],
                      observed_sha256=observed, observed_bytes=used)
    except FileNotFoundError:
        result['state'] = 'missing_source_file'
    except (OSError, WikiError) as exc:
        result.update(state='unavailable_source_file', code=error_code(exc))
    return result


def health(root, scope=None, now=None, verify_source=None, max_chars=12000):
    if type(max_chars) is not int or not 2048 <= max_chars <= 1000000:
        raise WikiError('max-chars must be 2048..1000000')
    selected_sources = sorted(set(verify_source or []))
    if len(selected_sources) > 16:
        raise WikiError('At most 16 sources may be checked')
    for source_id in selected_sources:
        identifier(source_id)
    at = annotations.canonical_time(now if now is not None else datetime.now(timezone.utc))
    instant = timestamp(at)
    findings, assessments, declared_hashes = [], {}, []
    dropped = 0
    complete = True
    detail_count = 0

    def finding(path, field, kind, action, observed=None, severity='warning'):
        nonlocal dropped, complete
        if len(findings) >= FINDING_LIMIT:
            dropped += 1
            complete = False
            return
        item = {'severity': severity, 'path': path, 'field': field, 'kind': kind, 'action': action}
        if observed is not None:
            item['observed'] = observed
        findings.append(item)

    def refs(path, field, values):
        nonlocal detail_count, complete
        if not values:
            finding(path, field, 'missing_evidence', 'record_evidence_or_keep_uncertainty')
        for ref in values:
            if detail_count >= FINDING_LIMIT:
                complete = False
                return
            detail_count += 1
            if 'sha256' in ref:
                declared_hashes.append((path, field, ref['resource'], ref['sha256']))

    def observe(node, meta):
        nonlocal complete
        path = node['path']
        if 'stale_after' in meta and instant >= timestamp(meta['stale_after']):
            deadline = timestamp(meta['stale_after'])
            try:
                observed = deadline.astimezone(timezone.utc).isoformat()
            except OverflowError:
                observed = deadline.isoformat()
            finding(path, 'stale_after', 'note_due', 'reconsider_note_currency', observed)
        if annotations.KEY not in meta:
            finding(path, annotations.KEY, 'missing_declarations', 'declare_observation_or_pointer_when_needed', severity='info')
            return
        errors = {}
        try:
            owned = annotations.stored_root(meta[annotations.KEY], node['id'], section_errors=errors)
        except (WikiError, UnicodeError, ValueError, TypeError, RecursionError):
            complete = False
            return
        for name in annotations.SECTIONS:
            if name in errors:
                complete = False
                finding(path, name, 'invalid_section', 'inspect_section_schema')
        if 'freshness' not in owned:
            finding(path, 'freshness', 'missing_freshness_declaration', 'declare_form_if_current_state_matters', severity='info')
        elif 'freshness' not in errors:
            value = owned['freshness']['data']
            refs(path, 'freshness.evidence', value['evidence'])
            for key in ('observed_at', 'last_observed_at'):
                if key in value and timestamp(value[key]) > instant:
                    finding(path, 'freshness.' + key, 'future_observation', 'inspect_declared_observation_time', value[key])
            if value['form'] == 'pointer':
                refs(path, 'freshness.target', [value['target']])
                if 'last_observed_at' not in value:
                    finding(path, 'freshness.last_observed_at', 'pointer_unobserved', 'consult_declared_home_system')
                if 'recheck_after' in value and instant >= timestamp(value['recheck_after']):
                    finding(path, 'freshness.recheck_after', 'pointer_due', 'reobserve_or_revise_pointer', value['recheck_after'])
        if 'context' in owned and 'context' not in errors:
            for name in ('completed', 'decisions', 'open_questions', 'next_actions', 'lessons'):
                for item in owned['context']['data'].get(name, []):
                    refs(path, 'context.' + name + '.' + item['id'], item['evidence'])
        sources = meta.get('sources', [])
        source_keys = set()
        for source in sources:
            try:
                source_keys.add(annotations.source_key(source['resource'], path))
            except (WikiError, ValueError, TypeError):
                complete = False
                finding(path, 'sources', 'invalid_source_reference', 'inspect_declared_source')
        labeled = set()
        if 'source_evidence' in owned and 'source_evidence' not in errors:
            for item in owned['source_evidence']['data']['items']:
                key = annotations.source_key(item['resource'], path)
                labeled.add(key)
                if key not in source_keys:
                    finding(path, 'source_evidence', 'unlinked_assessment', 'match_assessment_to_note_source', key)
                refs(path, 'source_evidence.evidence', item['evidence'])
                assessments.setdefault(key, []).append((path, item['provenance_basis'], item['retained_scope']))
                if item['retained_scope'] in ('locator_only', 'unknown') or item['provenance_basis'] in ('derived', 'unknown'):
                    finding(path, 'source_evidence', 'limited_declared_evidence', 'corroborate_or_retain_uncertainty',
                            {'resource': key, 'basis': item['provenance_basis'], 'retained_scope': item['retained_scope']})
        if source_keys - labeled:
            finding(path, 'source_evidence', 'unassessed_sources', 'declare_basis_if_useful', {'count': len(source_keys - labeled)}, 'info')

    raw_report, edges, diagnostics = _graph(root, scope=scope, observer=observe, return_raw=True)
    diagnostics = [dict(item) for item in diagnostics]
    for item in diagnostics:
        if item['kind'] in {'invalid_' + name for name in annotations.SECTIONS}:
            item['affects_analysis'] = True
        if item['kind'] in ('missing_indexed', 'unavailable_indexed', 'invalid_note', 'invalid_annotations', 'unsupported_sections', 'invalid_reference'):
            finding(item['path'], 'structure', item['kind'], 'inspect_reported_path_or_schema')
    for edge in edges:
        state = edge['resolution']
        if state != 'resolved':
            finding(edge['from']['path'], 'connections', state, 'inspect_reference_within_authorized_scope',
                    edge['target'], 'info' if state in ('wanted_not_indexed', 'out_of_scope', 'non_current_reference', 'unchecked_resource') else 'warning')
    for resource, declarations in sorted(assessments.items()):
        if len({(basis, retained) for _, basis, retained in declarations}) > 1:
            finding(None, 'source_evidence', 'assessment_disagreement', 'inspect_declared_assessments_without_adjudicating',
                    {'resource': resource, 'paths': sorted({path for path, _, _ in declarations})})
    io = {'bytes_read': 0, 'byte_limit': VERIFY_BYTES, 'complete': True,
          'requested_count': len(selected_sources), 'requested_sha256': digest(encoded(selected_sources))}
    checked = []
    with Store(root) as store:
        for source_id in selected_sources:
            result = verify(store, source_id, io)
            checked.append(result)
            if result['state'] not in ('matched', 'hash_mismatch'):
                io['complete'] = False
            if result['state'] != 'matched':
                finding('/sources/' + source_id, 'verification', result['state'], 'inspect_captured_bytes_without_truth_inference')
            if result['state'] in ('matched', 'hash_mismatch'):
                resource = f'/sources/{source_id}/content.raw'
                for path, field, ref, expected in declared_hashes:
                    if ref == resource and expected != result['observed_sha256']:
                        finding(path, field, 'declared_hash_mismatch', 'inspect_declared_evidence_bytes', {'resource': resource})
    report = {'schema_version': 1, 'command': 'health', 'data_only': True,
              'guidance': 'Structural recommendations only; declarations and matching hashes do not verify facts. Nothing is repaired or fetched.',
              'scope': raw_report['scope'], 'evaluated_at': at, 'consistency': 'best_effort',
              'index_changed': raw_report['index_changed'], 'scan': raw_report['scan'], 'verification_io': io,
              'analysis_references': {'processed': detail_count, 'limit': FINDING_LIMIT},
              'analysis_complete': raw_report['analysis_complete'] and complete and io['complete'],
              'output_complete': True, 'partial': False, 'counts': {},
              'omitted': {'diagnostics': raw_report['omitted']['diagnostics'], 'findings': dropped, 'verification': 0},
              'diagnostics': [], 'findings': [], 'verification': []}
    counts = {severity: sum(item['severity'] == severity for item in findings) for severity in ('warning', 'info')}
    report['counts'] = {'findings_observed': len(findings), 'findings_total': len(findings) if report['analysis_complete'] and report['scan']['complete'] else None, **counts}
    findings.sort(key=lambda item: (0 if item['severity'] == 'warning' else 1, item['path'] or '', item['field'], item['kind'], encoded(item.get('observed'))))
    return pack(report, {'diagnostics': diagnostics, 'verification': checked, 'findings': findings}, max_chars)
