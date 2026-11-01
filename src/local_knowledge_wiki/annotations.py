"""Explicit, bounded work-context declarations; no evidence is fetched here."""

import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .errors import WikiError
from .format import local_target, timestamp
from .limits import check_size
from .storage import identifier, read_input, single_line


KEY = 'x-second-brain-annotations'
INPUT_BYTES = ROOT_BYTES = 262144
SECTION_BYTES = 65536
DEPTH_LIMIT = 8
VALUE_LIMIT = 4096


def fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise WikiError('Invalid annotation fields; required: ' + ', '.join(required))


def text(value, field, maximum=1024, line=False):
    if not isinstance(value, str) or not value.strip():
        raise WikiError(f'{field} must be a nonempty string')
    try:
        check_size(len(value.encode('utf-8')), maximum, field)
    except UnicodeError as exc:
        raise WikiError(f'{field} must contain valid UTF-8') from exc
    if line:
        single_line(value, field)
        if any(unicodedata.category(c).startswith('C') for c in value):
            raise WikiError(f'{field} must not contain control characters')
    return value


def local_id(value):
    text(value, 'annotation ID', 64, line=True)
    return identifier(value)


def actor(value):
    text(value, 'annotation actor', 64, line=True)
    if not re.fullmatch(r'(?:human:[^\s:/\\]+|process:[^\s:/\\]+|[^\s:/\\]+/[^\s:/\\]+)', value):
        raise WikiError('Annotation actor must be human:ID, process:ID or PRODUCER/VERSION')
    return value


def canonical_time(value):
    if isinstance(value, str) and re.search(r'\.\d{7}', value):
        raise WikiError('Annotation time supports at most 6 fractional-second digits')
    if not isinstance(value, (str, datetime)):
        raise WikiError('Annotation time must be an explicit-offset ISO8601 instant')
    try:
        return timestamp(value).astimezone(timezone.utc).isoformat()
    except OverflowError as exc:
        raise WikiError('Annotation time is outside the supported UTC range') from exc


def json_bytes(value, max_bytes=None, label='stored annotations'):
    """Admit exact escaped UTF-8 size before encoding an alias-expanded owned tree."""
    maximum = ROOT_BYTES if max_bytes is None else max_bytes
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    active = set()
    visited = 0
    size = 0

    def add(count):
        nonlocal size
        size += count
        check_size(size, maximum, label)

    def visit(item, depth):
        nonlocal visited
        visited += 1
        if depth > DEPTH_LIMIT or visited > VALUE_LIMIT:
            raise WikiError('Annotation depth/value limit exceeded', 'input_too_large')
        if isinstance(item, (dict, list)):
            identity = id(item)
            if identity in active:
                raise WikiError('Cyclic annotation data is unsupported')
            active.add(identity)
            add(2)
            if isinstance(item, dict):
                if any(not isinstance(key, str) for key in item):
                    raise WikiError('Annotation keys must be strings')
                for index, (key, child) in enumerate(item.items()):
                    if index:
                        add(1)
                    visit(key, depth + 1)
                    add(1)
                    visit(child, depth + 1)
            else:
                for index, child in enumerate(item):
                    if index:
                        add(1)
                    visit(child, depth + 1)
            active.remove(identity)
        elif isinstance(item, str):
            add(2)
            for character in item:
                code = ord(character)
                if 0xD800 <= code <= 0xDFFF:
                    raise UnicodeError('Surrogate annotation character')
                if character in ('"', '\\'):
                    add(2)
                elif code < 0x20:
                    add(2 if code in (8, 9, 10, 12, 13) else 6)
                else:
                    add(1 if code < 0x80 else 2 if code < 0x800 else 3 if code < 0x10000 else 4)
        else:
            if item is not None and type(item) not in (bool, int, float):
                raise WikiError('Annotation values must be JSON-compatible')
            if isinstance(item, float) and not math.isfinite(item):
                raise WikiError('Nonfinite annotation numbers are unsupported')
            if type(item) is int:
                # A conservative decimal-digit lower bound rejects enormous integers
                # before their decimal conversion; the encoder supplies exact length.
                check_size(size + max(1, (item.bit_length() - 1) * 3 // 10 + 1)
                           + (item < 0), maximum, label)
            add(len(encoder.encode(item)))

    try:
        visit(value, 0)
        output = bytearray()
        for chunk in encoder.iterencode(value):
            block = chunk.encode('utf-8')
            check_size(len(output) + len(block), maximum, label)
            output.extend(block)
        return bytes(output)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise WikiError('Annotation data must be bounded, valid UTF-8 JSON') from exc


def load_input(path):
    raw = read_input(path, max_bytes=INPUT_BYTES)

    def mapping(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise WikiError('Duplicate annotation JSON key')
            result[key] = value
        return result

    def constant(_):
        raise WikiError('Nonfinite annotation numbers are unsupported')

    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=mapping, parse_constant=constant)
        json_bytes(value)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise WikiError('Annotation input must be strict UTF-8 JSON') from exc
    return raw, value


def evidence(value):
    if not isinstance(value, list) or len(value) > 8:
        raise WikiError('Evidence must be a list of at most 8 references')
    for item in value:
        fields(item, ('resource',), ('sha256',))
        resource = text(item['resource'], 'evidence resource', 2048, line=True)
        if resource != resource.strip():
            raise WikiError('Evidence resource must not have surrounding whitespace')
        parsed = urlsplit(resource)
        if parsed.scheme:
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname or not parsed.netloc
                    or parsed.username is not None or parsed.password is not None
                    or any(c.isspace() or c in '<>"{}|^`\\' for c in resource)
                    or re.search(r'%(?![0-9a-fA-F]{2})', resource)):
                raise WikiError('Evidence URL must be absolute HTTP(S) without credentials')
            host = parsed.hostname.encode('idna').decode('ascii')
            if ':' not in host and not all(re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', part)
                                            for part in host.rstrip('.').split('.')):
                raise WikiError('Invalid evidence URL host')
            if parsed.netloc.endswith(':') or (parsed.port is not None and not 1 <= parsed.port <= 65535):
                raise WikiError('Invalid evidence URL port')
        else:
            if (not resource.startswith('/') or parsed.netloc or '?' in resource or '#' in resource
                    or '\\' in resource or any(p in ('', '.', '..', '.git', '.obsidian') or p.startswith('.lkw')
                                              for p in resource[1:].split('/'))):
                raise WikiError('Evidence must use a safe literal bundle-root path')
        if 'sha256' in item and (not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
            raise WikiError('Declared evidence sha256 must be 64 lowercase hex digits')


def context_data(value):
    fields(value, ('work_id', 'recipients', 'completed', 'decisions', 'open_questions', 'lessons'), ('next_actions',))
    local_id(value['work_id'])
    recipients = value['recipients']
    if not isinstance(recipients, list) or not 1 <= len(recipients) <= 16:
        raise WikiError('Context needs 1..16 unique recipient labels')
    for label in recipients:
        text(label, 'recipient', 64, line=True)
    if len(set(recipients)) != len(recipients):
        raise WikiError('Duplicate context recipient')
    for name in ('completed', 'decisions', 'open_questions', 'next_actions', 'lessons'):
        records = value.get(name, [])
        if not isinstance(records, list) or len(records) > 32:
            raise WikiError(f'{name} must contain at most 32 records')
        ids = set()
        for record in records:
            fields(record, ('id', 'text', 'evidence', 'review') if name == 'lessons' else ('id', 'text', 'evidence'))
            local_id(record['id'])
            if record['id'] in ids:
                raise WikiError(f'Duplicate {name} record ID')
            ids.add(record['id'])
            text(record['text'], name + ' text')
            evidence(record['evidence'])
            if name == 'lessons':
                review = record['review']
                if isinstance(review, dict) and review.get('status') == 'proposed':
                    fields(review, ('status',))
                else:
                    fields(review, ('status', 'by', 'at', 'reason'))
                    if review['status'] not in ('accepted', 'rejected'):
                        raise WikiError('Lesson review must be proposed, accepted or rejected')
                    actor(review['by'])
                    if not isinstance(review['at'], str):
                        raise WikiError('Lesson review at must be a timestamp string')
                    canonical_time(review['at'])
                    text(review['reason'], 'lesson review reason')
    return value


RELATION_TYPES = ('relates_to', 'depends_on', 'supersedes', 'contradicts', 'supports')
SECTIONS = ('context', 'relations', 'freshness', 'source_evidence')


def relations_data(value, owner_id=None):
    fields(value, ('items',))
    if not isinstance(value['items'], list) or len(value['items']) > 128:
        raise WikiError('Relations must contain at most 128 items')
    ids = set()
    for item in value['items']:
        fields(item, ('id', 'type', 'target', 'expectation', 'evidence'))
        local_id(item['id'])
        if item['id'] in ids:
            raise WikiError('Duplicate relation ID')
        ids.add(item['id'])
        if item['type'] not in RELATION_TYPES:
            raise WikiError('Unknown declared relation type')
        fields(item['target'], ('id',), ('revision',))
        local_id(item['target']['id'])
        if item['target']['id'] == owner_id:
            raise WikiError('Self-concept relations are unsupported')
        if 'revision' in item['target']:
            revision = item['target']['revision']
            if not isinstance(revision, str) or not re.fullmatch(r'r(?!000000)[0-9]{6}', revision):
                raise WikiError('Relation revision must be r000001 through r999999')
        if item['expectation'] not in ('required', 'wanted'):
            raise WikiError('Relation expectation must be required or wanted')
        if item['expectation'] == 'wanted' and 'revision' in item['target']:
            raise WikiError('Wanted relations require an unversioned concept target')
        evidence(item['evidence'])
    return value


def freshness_data(value):
    if not isinstance(value, dict):
        raise WikiError('Freshness must be an object')
    form = value.get('form')
    if form == 'observation':
        fields(value, ('form', 'observed_at', 'evidence'))
    elif form == 'pointer':
        fields(value, ('form', 'target', 'evidence'), ('last_observed_at', 'recheck_after'))
        evidence([value['target']])
    elif form == 'reference':
        fields(value, ('form', 'evidence'))
    else:
        raise WikiError('Freshness form must be observation, pointer or reference')
    for key in ('observed_at', 'last_observed_at', 'recheck_after'):
        if key in value:
            if not isinstance(value[key], str):
                raise WikiError('Freshness timestamps must be strings')
            canonical_time(value[key])
    evidence(value['evidence'])
    return value


def source_key(resource, note_path):
    text(resource, 'source resource', 2048, line=True)
    if resource.startswith(('./', '../', '/')):
        target = local_target(note_path, resource)
        evidence([{'resource': '/' + target}])
        return '/' + target
    return resource


def source_evidence_data(value, sources=None, note_path=None):
    fields(value, ('items',))
    if not isinstance(value['items'], list) or len(value['items']) > 32:
        raise WikiError('Source evidence must contain at most 32 items')
    keys = None if sources is None else {source_key(s['resource'], note_path) for s in sources}
    for item in value['items']:
        fields(item, ('resource', 'provenance_basis', 'retained_scope', 'rationale', 'evidence'))
        key = source_key(item['resource'], note_path)
        if keys is not None and key not in keys:
            raise WikiError('Source assessment must identify a declared note source')
        if item['provenance_basis'] not in ('primary_record', 'direct_document', 'derived', 'unknown'):
            raise WikiError('Unsupported declared provenance basis')
        if item['retained_scope'] not in ('complete', 'excerpt', 'locator_only', 'unknown'):
            raise WikiError('Unsupported declared retained scope')
        text(item['rationale'], 'source assessment rationale')
        evidence(item['evidence'])
    return value


def section_data(name, value, owner_id=None, sources=None):
    if name == 'context':
        return context_data(value)
    if name == 'relations':
        return relations_data(value, owner_id)
    if name == 'freshness':
        return freshness_data(value)
    if name == 'source_evidence':
        return source_evidence_data(value, sources, f'concepts/{owner_id}/r000001.md')
    raise WikiError('Unsupported annotation section')


def envelope(data, by, at, section='context', owner_id=None, sources=None):
    section_data(section, data, owner_id, sources)
    if section == 'freshness':
        for key in ('observed_at', 'last_observed_at', 'recheck_after'):
            if key in data:
                data[key] = canonical_time(data[key])
    for lesson in data.get('lessons', []) if section == 'context' else []:
        if 'at' in lesson['review']:
            lesson['review']['at'] = canonical_time(lesson['review']['at'])
    value = {'recorded_by': actor(by), 'recorded_at': canonical_time(at), 'data': data}
    json_bytes(value, SECTION_BYTES, 'stored ' + section + ' section')
    return value


def stored_root(value, owner_id=None, *, section_errors=None, sources=None):
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        raise WikiError('Unsupported annotation root/version')
    json_bytes(value, ROOT_BYTES, 'stored annotations')
    for name, section in value.items():
        if name == 'version':
            continue
        try:
            json_bytes(section, SECTION_BYTES, 'stored annotation section')
            if name in SECTIONS:
                fields(section, ('recorded_by', 'recorded_at', 'data'))
                actor(section['recorded_by'])
                if not isinstance(section['recorded_at'], str):
                    raise WikiError('recorded_at must be a timestamp string')
                canonical_time(section['recorded_at'])
                section_data(name, section['data'], owner_id, sources)
        except (WikiError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
            if section_errors is None or name not in SECTIONS:
                raise
            section_errors[name] = exc
    return value


def author_root(path, by, at, owner_id=None, sources=None):
    raw, value = load_input(path)
    fields(value, ('version',), SECTIONS)
    if type(value['version']) is not int or value['version'] != 1:
        raise WikiError('Annotation version must be integer 1')
    if not any(name in value for name in SECTIONS):
        raise WikiError('Annotation input needs an implemented section')
    result = {'version': 1}
    for name in SECTIONS:
        if name in value:
            result[name] = envelope(value[name], by, at, name, owner_id, sources)
    stored_root(result, owner_id, sources=sources)
    return raw, result
