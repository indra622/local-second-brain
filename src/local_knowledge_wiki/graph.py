"""Deterministic declared/current graph; references are never fetched or executed."""

import re
from collections import Counter, deque
from urllib.parse import unquote, urlsplit

from . import annotations
from .context import DIAGNOSTIC_LIMIT, NOTE_LIMIT, READ_BYTES, REFERENCE_LIMIT
from .errors import WikiError, error_code
from .format import local_target, parse, validate
from .limits import file_limit
from .reading import REVISION_PATH
from .recall import render
from .requests import digest, encoded
from .storage import Store, current_index


EDGE_TYPES = (*annotations.RELATION_TYPES, 'link', 'source')
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
TICKS = re.compile(r'`+')
LINK = re.compile(r'\[[^\]\n]*\]\(([^\s()]+)\)')


def markdown_links(body):
    """Simple inline links, excluding fenced blocks and equal-run backtick spans."""
    body = body.replace('\r\n', '\n').replace('\r', '\n')
    fence = None
    lines = []
    for line in body.splitlines(keepends=True):
        marker = FENCE.match(line)
        if fence is None and marker:
            fence = marker[1]
            lines.append('\n' if line.endswith('\n') else '')
        elif fence is not None:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            lines.append('\n' if line.endswith('\n') else '')
        else:
            lines.append(line)
    visible = ''.join(lines)
    remaining = Counter(len(match[0]) for match in TICKS.finditer(visible))
    pieces = []
    start = None
    width = None
    end = 0
    for match in TICKS.finditer(visible):
        length = len(match[0])
        remaining[length] -= 1
        if start is None and remaining[length]:
            start, width = match.start(), length
        elif start is not None and length == width:
            hidden = re.sub(r'[^\n]+', ' ', visible[start:match.end()])
            pieces.extend((visible[end:start], hidden))
            end = match.end()
            start = None
    pieces.append(visible[end:])
    for number, line in enumerate(''.join(pieces).splitlines(), 1):
        for match in LINK.finditer(line):
            yield match[1], number


def resource_target(path, resource, source=False):
    if not isinstance(resource, str) or len(resource) > 2048:
        raise WikiError('Graph resource exceeds supported string limit', 'input_too_large')
    annotations.text(resource, 'graph resource', 2048, line=True)
    parsed = urlsplit(resource)
    if parsed.scheme:
        annotations.evidence([{'resource': resource}])
        return {'resource': resource}
    if source and not resource.startswith(('./', '../', '/')):
        return {'resource': resource}
    parts = unquote(parsed.path).split('/')
    if parsed.netloc or any(part in ('.git', '.obsidian') or part.startswith('.lkw') for part in parts):
        raise WikiError('Unsafe graph reference', 'unsafe_path')
    target = local_target(path, resource)
    if target is None:
        return {'resource': resource}
    identity = REVISION_PATH.fullmatch(target)
    if identity and identity[2] != 'r000000':
        return {'id': identity[1], 'revision': identity[2]}
    return {'resource': '/' + target}


def pack(report, records, max_chars):
    """Select deterministic whole-record prefixes with logarithmic formatting passes."""
    totals = {name: len(items) for name, items in records.items()}
    dropped_diagnostics = report['omitted']['diagnostics']

    def update():
        for name, total in totals.items():
            report['omitted'][name] = total - len(report[name])
        report['omitted']['diagnostics'] += dropped_diagnostics
        report['output_complete'] = not any(report['omitted'].values())
        report['partial'] = not (report['scan']['complete'] and report['analysis_complete'] and report['output_complete'])

    update()
    if len(render(report)) > max_chars:
        raise WikiError('Graph envelope cannot fit output budget')
    for name, items in records.items():
        low, high = 0, len(items)
        while low < high:
            middle = (low + high + 1) // 2
            report[name] = items[:middle]
            update()
            if len(render(report)) <= max_chars:
                low = middle
            else:
                high = middle - 1
        report[name] = items[:low]
        update()
    return report


def graph(root, scope=None, backlinks=None, path=None, relation=None, max_depth=None, max_chars=12000):
    if type(max_chars) is not int or not 2048 <= max_chars <= 1000000:
        raise WikiError('max-chars must be 2048..1000000')
    if backlinks is not None and path is not None:
        raise WikiError('Choose backlinks or path, not both')
    if max_depth is not None and path is None:
        raise WikiError('max-depth requires --path')
    depth = 3 if max_depth is None else max_depth
    if type(depth) is not int or not 1 <= depth <= 8:
        raise WikiError('max-depth must be 1..8')
    ids = sorted(set(scope or []))
    for value in ids:
        annotations.local_id(value)
    endpoints = list(path) if path is not None else [backlinks] if backlinks is not None else []
    if path is not None and len(endpoints) != 2:
        raise WikiError('Path needs two concept IDs')
    for value in endpoints:
        annotations.local_id(value)
    types = sorted(set(EDGE_TYPES if relation is None else relation))
    if any(value not in EDGE_TYPES for value in types):
        raise WikiError('Unsupported graph relation filter')
    mode = 'path' if path is not None else 'backlinks' if backlinks is not None else 'overview'
    report = {'schema_version': 1, 'command': 'graph', 'data_only': True,
              'guidance': 'Declared structure, not semantic proof. Terminal references are unopened.',
              'scope': {'selection': 'indexed-current', 'explicit': scope is not None,
                        'requested_count': len(ids) if scope is not None else None,
                        'requested_sha256': digest(encoded(ids)) if scope is not None else None},
              'query': {'mode': mode, 'endpoints': endpoints, 'relations': types,
                        'max_depth': depth if path is not None else None},
              'parser': 'simple-inline-v1; code excluded; no CommonMark/wiki/aliases',
              'consistency': 'best_effort', 'index_changed': False,
              'scan': {'selected': 0, 'processed': 0, 'read_bytes': 0, 'budget_charged_bytes': 0,
                       'references': 0, 'complete': True,
                       'limits': {'notes': NOTE_LIMIT, 'note_bytes': READ_BYTES,
                                  'references': REFERENCE_LIMIT, 'diagnostics': DIAGNOSTIC_LIMIT}},
              'analysis_complete': True, 'output_complete': True, 'partial': False,
              'counts': {}, 'path_state': None, 'path_length': None,
              'omitted': {'paths': 0, 'diagnostics': 0, 'edges': 0, 'nodes': 0},
              'paths': [], 'diagnostics': [], 'edges': [], 'nodes': []}
    scan = report['scan']
    diagnostics, pending, nodes = [], [], {}
    reference_limited = False

    def diagnostic(note_path, kind, exc=None, affects_analysis=True):
        if affects_analysis:
            report['analysis_complete'] = False
        if len(diagnostics) >= DIAGNOSTIC_LIMIT:
            report['omitted']['diagnostics'] += 1
            return
        item = {'path': note_path, 'kind': kind, 'affects_analysis': affects_analysis}
        if exc is not None:
            message = str(exc)
            item.update(code=error_code(exc), message=message[:240], message_truncated=len(message) > 240)
        diagnostics.append(item)

    def admit(node):
        nonlocal reference_limited
        if scan['references'] >= REFERENCE_LIMIT:
            scan['complete'] = False
            reference_limited = True
            diagnostic(node['path'], 'reference_limit')
            return False
        scan['references'] += 1
        return True

    def mention(node, edge_type, origin, target, expectation, provenance, admitted=False):
        if not admitted and not admit(node):
            return False
        if edge_type in types:
            pending.append((node, edge_type, origin, target, expectation, provenance))
        return True

    with Store(root) as store:
        try:
            before = store.read('index.md')
            entries = current_index(before.decode('utf-8'))[0]
        except (OSError, WikiError, UnicodeError) as exc:
            raise WikiError('Graph requires a readable valid current index', 'invalid_index') from exc
        if scope is not None and any(value not in entries for value in ids):
            raise WikiError('A requested graph ID is not indexed', 'not_found')
        selected = set(ids if scope is not None else entries)
        if any(value not in selected for value in endpoints):
            raise WikiError('Graph endpoints must be selected indexed concepts')
        scan['selected'] = len(selected)
        for ident in sorted(selected, key=lambda value: entries[value]):
            remaining = READ_BYTES - scan['budget_charged_bytes']
            if scan['processed'] >= NOTE_LIMIT or remaining <= 0:
                scan['complete'] = False
                diagnostic(None, 'scan_limit')
                break
            scan['processed'] += 1
            note_path = entries[ident]
            revision = REVISION_PATH.fullmatch(note_path)
            node = {'id': ident, 'revision': revision[2], 'path': note_path,
                    'sha256': None, 'availability': 'unavailable_indexed'}
            nodes[ident] = node
            if revision[2] == 'r000000':
                diagnostic(note_path, 'unsupported_revision')
                scan['complete'] = False
                continue
            try:
                raw = store.read(note_path, budget_bytes=remaining)
            except (OSError, WikiError) as exc:
                node['availability'] = 'missing_indexed' if isinstance(exc, FileNotFoundError) else 'unavailable_indexed'
                scan['budget_charged_bytes'] += min(file_limit(note_path), remaining)
                scan['read_bytes'] = None
                scan['complete'] = False
                diagnostic(note_path, node['availability'], exc)
                continue
            scan['budget_charged_bytes'] += len(raw)
            if scan['read_bytes'] is not None:
                scan['read_bytes'] += len(raw)
            node['sha256'] = digest(raw)
            try:
                meta, body = parse(raw.decode('utf-8'))
                errors = validate(meta)
                if errors:
                    raise WikiError('; '.join(errors))
            except (WikiError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
                node['availability'] = 'invalid_indexed'
                diagnostic(note_path, 'invalid_note', exc)
                continue
            node['availability'] = 'readable'
            if any(value in annotations.RELATION_TYPES for value in types) and annotations.KEY in meta:
                try:
                    section_errors = {}
                    owned = annotations.stored_root(meta[annotations.KEY], ident, section_errors=section_errors)
                    for name, exc in sorted(section_errors.items()):
                        diagnostic(note_path, 'invalid_' + name, exc, affects_analysis=name == 'relations')
                    if owned.keys() - {'version', *annotations.SECTIONS}:
                        diagnostic(note_path, 'unsupported_sections')
                    if 'relations' in owned and 'relations' not in section_errors:
                        section = owned['relations']
                        for item in section['data']['items']:
                            if not mention(node, item['type'], 'annotation', item['target'], item['expectation'],
                                           {'id': item['id'], 'recorded_by': section['recorded_by'],
                                            'recorded_at': annotations.canonical_time(section['recorded_at']),
                                            'evidence': item['evidence'], 'evidence_hashes': 'declared_not_checked'}):
                                break
                except (WikiError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
                    diagnostic(note_path, 'invalid_annotations', exc)
            if reference_limited:
                break
            for edge_type, origin, references in (
                    ('link', 'markdown', markdown_links(body) if 'link' in types else ()),
                    ('source', 'sources', ((item['resource'], number) for number, item in
                                          enumerate(meta.get('sources', []), 1)) if 'source' in types else ())):
                for resource, position in references:
                    if not admit(node):
                        break
                    try:
                        target = resource_target(note_path, resource, source=edge_type == 'source')
                        if not mention(node, edge_type, origin, target, 'required',
                                       {'resource': resource, 'line' if edge_type == 'link' else 'source_index': position}, admitted=True):
                            break
                    except (WikiError, UnicodeError, ValueError, TypeError) as exc:
                        diagnostic(note_path, 'invalid_reference', exc)
                if reference_limited:
                    break
            if reference_limited:
                break
        try:
            report['index_changed'] = store.read('index.md') != before
        except (OSError, WikiError):
            report['index_changed'] = True
        if report['index_changed']:
            scan['complete'] = False
            diagnostic('index.md', 'index_changed')

    def resolve(target, expectation):
        if 'id' not in target:
            return 'unchecked_resource', None
        ident = target['id']
        if ident not in entries:
            return ('wanted_not_indexed' if expectation == 'wanted' else 'not_indexed'), None
        if ident not in selected:
            return 'out_of_scope', None
        if 'revision' in target and target['revision'] != REVISION_PATH.fullmatch(entries[ident])[2]:
            return 'non_current_reference', None
        state = nodes[ident]['availability'] if ident in nodes else 'unread_indexed'
        return ('resolved' if state == 'readable' else state), entries[ident]

    groups = {}
    for node, edge_type, origin, target, expectation, provenance in pending:
        key = (node['path'], edge_type, origin, encoded(target), expectation)
        if key not in groups:
            state, target_path = resolve(target, expectation)
            groups[key] = {'from': node, 'type': edge_type, 'origin': origin, 'target': target,
                           'expectation': expectation, 'resolution': state, 'target_path': target_path,
                           'target_sha256': nodes.get(target.get('id'), {}).get('sha256') if state == 'resolved' else None,
                           'traversable': state == 'resolved', 'count': 0, 'provenance': []}
        edge = groups[key]
        edge['count'] += 1
        edge['provenance'].append(provenance)
    edges = [groups[key] for key in sorted(groups)]
    complete = scan['complete'] and report['analysis_complete']
    paths = []
    if mode == 'backlinks':
        edges = [edge for edge in edges if edge['target_path'] == entries[backlinks]]
    elif mode == 'path':
        adjacency = {}
        for edge in edges:
            if edge['traversable']:
                adjacency.setdefault(edge['from']['id'], []).append(edge)
        for outgoing in adjacency.values():
            outgoing.sort(key=lambda edge: (edge['target_path'], edge['type'], edge['origin'],
                                           edge['provenance'][0].get('id', '')))
        queue = deque([(endpoints[0], [])])
        seen = {endpoints[0]}
        found = None
        if all(value in nodes and nodes[value]['availability'] == 'readable' for value in endpoints):
            while queue:
                ident, steps = queue.popleft()
                if ident == endpoints[1]:
                    found = steps
                    break
                if len(steps) >= depth:
                    continue
                for edge in adjacency.get(ident, []):
                    next_id = edge['target']['id']
                    if next_id not in seen:
                        seen.add(next_id)
                        queue.append((next_id, steps + [edge]))
        if found is not None:
            report['path_state'] = 'found' if complete else 'found_partial'
            report['path_length'] = len(found)
            paths = [{'length': len(found), 'shortest_proven': complete, 'steps': found}]
        else:
            report['path_state'] = 'no_path_within_depth' if complete else 'undetermined'
        edges = []
    report['counts'] = {'nodes_observed': len(nodes), 'edges_observed': len(groups),
                        'matching_edges_observed': len(edges),
                        'nodes_total': len(nodes) if complete else None,
                        'edges_total': len(groups) if complete else None}
    diagnostics.sort(key=lambda item: (item['path'] or '', item['kind']))
    return pack(report, {'paths': paths, 'diagnostics': diagnostics, 'edges': edges,
                         'nodes': [nodes[key] for key in sorted(nodes)]}, max_chars)
