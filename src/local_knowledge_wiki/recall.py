"""Bounded current-note context; references are data, never fetched."""

import json
import math
import re
from collections import Counter

from .reading import REVISION_PATH, read_note
from .storage import Store, WikiError, current_index


def render(result):
    return json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def words(text):
    return re.findall(r'\w+', text.casefold())


def matches(term, word, mode):
    expandable = len(term) >= 3 or re.fullmatch(r'[가-힣]{2,}', term) is not None
    return term == word or (mode == 'lexical' and expandable and word.startswith(term))


# Unknown fields, including arbitrary extension trees, are deliberately not traversed.
FIELDS = ('id', 'resource', 'last_modified', 'by', 'at', 'sha256',
          'x-second-brain-target', 'x-second-brain-evidence')


def selected(value, omitted, depth=0):
    if depth >= 4:
        omitted.append(True)
        return None
    if isinstance(value, dict):
        if any(key not in FIELDS for key in value):
            omitted.append(True)
        return {key: selected(value[key], omitted, depth + 1) for key in FIELDS if key in value}
    if isinstance(value, list):
        if len(value) > 8:
            omitted.append(True)
        return [selected(item, omitted, depth + 1) for item in value[:8]]
    if isinstance(value, float) and not math.isfinite(value):
        omitted.append(True)
        return None
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    if len(text) > 240:
        omitted.append(True)
        return text[:239] + '…'
    return text


def recall(root, query, now, match='auto', limit=5, max_chars=12000):
    terms = sorted(set(words(query)))
    if not terms:
        raise WikiError('Query needs at least one word')
    if match not in ('auto', 'exact', 'lexical'):
        raise WikiError('Match must be auto, exact or lexical')
    if not 1 <= limit <= 100 or not 2048 <= max_chars <= 1000000:
        raise WikiError('limit must be 1..100; max-chars must be 2048..1000000')
    result = {'state': 'no_match', 'requested_match': match, 'match_mode': 'exact',
              'fallback_used': False, 'scope': 'indexed-current-cli-revisions',
              'max_chars': max_chars, 'limit': limit, 'matched': 0, 'omitted_results': 0,
              'indexed': 0, 'excluded': {'unavailable': 0, 'unsupported_revision': 0, 'invalid_utf8': 0},
              'invalid_metadata_notes': 0,
              'results': [], 'guidance': ''}
    with Store(root) as store:
        try:
            current = current_index(store.read('index.md').decode('utf-8'))[0]
        except (FileNotFoundError, UnicodeError, WikiError):
            result.update(state='invalid_index', guidance='Inspect index.md and run check; current selection is unavailable. No historical substitution.')
            return result
        result['indexed'] = len(current)
        notes = []
        for path in sorted(current.values()):
            identity = REVISION_PATH.fullmatch(path)
            if not identity or identity[2] == 'r000000':
                result['excluded']['unsupported_revision'] += 1
                continue
            try:
                note, _ = read_note(store, path, now, current)
            except (OSError, WikiError):
                result['excluded']['unavailable'] += 1
                continue
            if note['metadata_errors'] == ['Note must be UTF-8']:
                result['excluded']['invalid_utf8'] += 1
                continue
            if note['metadata_errors']:
                result['invalid_metadata_notes'] += 1
            counts = Counter(words((note['title'] if isinstance(note['title'], str) else '') + '\n' + note['body']))
            notes.append((identity, note, counts))

    def retrieve(mode):
        hits = []
        for identity, note, counts in notes:
            scores = [sum(count for word, count in counts.items() if matches(t, word, mode)) for t in terms]
            if all(scores):
                hits.append((sum(scores), identity, note))
        return sorted(hits, key=lambda hit: (-hit[0], hit[2]['path']))

    mode = 'lexical' if match == 'lexical' else 'exact'
    hits = retrieve(mode)
    if not hits and match == 'auto':
        mode = 'lexical'
        result['fallback_used'] = True
        hits = retrieve(mode)
    result.update(match_mode=mode, matched=len(hits), omitted_results=len(hits))
    result['state'] = 'matches' if hits else ('empty_index' if not current else 'no_match')
    result['guidance'] = ('Use show BUNDLE ID --revision REVISION for full metadata/body; inspect authorized sources separately. Prefix matches may be unrelated. Trust labels are unauthenticated declarations.' if hits else
                          'No match is not proof of absence. Try broader or alternative words, inspect list/index and check; capture only separately authorized inputs.')
    if not hits and match == 'exact':
        result['guidance'] += ' Try --match lexical for explicit word-prefix expansion.'
    if result['invalid_metadata_notes']:
        result['guidance'] += ' Invalid metadata was observed; inspect metadata_errors with show/check.'
    if any(result['excluded'].values()):
        result['state'] = 'partial' if hits else 'incomplete'
        result['guidance'] += ' Indexed notes were excluded; inspect index and run check.'
    for score, identity, note in hits[:limit]:
        omitted = []
        meta = note['metadata']
        body = note['body']
        position = next((m.start() for m in re.finditer(r'\w+', body)
                         if any(matches(t, m[0].casefold(), mode) for t in terms)), 0)
        start = max(0, position - 120)
        end = min(len(body), start + 1600)
        item = {'id': identity[1], 'revision': identity[2], 'path': note['path'],
                'current': True, 'score': score,
                **{key: selected(note[key], omitted) for key in
                   ('title', 'status', 'trust', 'stale', 'stale_after', 'generated', 'verified', 'metadata_errors')},
                'sources': selected(meta.get('sources'), omitted),
                'metadata_omitted': True, 'selected_fields_truncated_or_omitted': bool(omitted),
                'body_start': start, 'body_end': end, 'body_chars': len(body),
                'body_truncated': start > 0 or end < len(body), 'body': body[start:end]}
        result['results'].append(item)
        result['omitted_results'] -= 1
        # Measure escaped JSON too: controls can occupy several output characters.
        while len(render(result)) > max_chars and item['body']:
            item['body'] = item['body'][:len(item['body']) // 2]
            item['body_end'] = start + len(item['body'])
            item['body_truncated'] = True
        if len(render(result)) > max_chars:
            result['results'].pop()
            result['omitted_results'] += 1
            break
    if hits and not result['results']:
        result['state'] = 'budget_omitted'
    return result
