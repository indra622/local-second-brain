"""Create-only request receipts, under the caller's bundle write lock.

Pending state is deliberately not reconciled automatically. These records prove
process-observed completion, not a database transaction or power-loss recovery.
"""

import hashlib
import json
import os
import re
import stat

from .storage import WikiError, identifier


ROOT = '.lkw-requests'


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False,
                      separators=(',', ':'), default=str).encode('ascii')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def expected_current(entries, concept_id, expected):
    if expected is None:
        return
    actual = entries.get(concept_id)
    wanted = None if expected == 'absent' else f'concepts/{concept_id}/{expected}.md'
    if actual != wanted:
        raise WikiError('Expected current revision does not match index; re-read before a new request',
                        'precondition_failed')


def validate_expected(expected):
    if expected is not None and expected != 'absent' and not re.fullmatch(r'r[0-9]{6}', expected):
        raise WikiError('Expected current must be absent or r000001 through r999999')
    if expected == 'r000000':
        raise WikiError('Expected current must be absent or r000001 through r999999')


def sync_receipt(store, folder):
    for path in (ROOT, folder, folder + '/intent.json'):
        with store.parent(path) as (fd, _):
            os.fsync(fd)


def effect_paths(command, payload, result):
    if command == 'capture':
        path = f"sources/{payload['id']}/content.raw"
        if result != path:
            raise ValueError('Unexpected capture result')
        return [path, f"sources/{payload['id']}/provenance.json"]
    path = result if command == 'curate' else result['revision']
    if not isinstance(path, str) or not re.fullmatch(
            r'concepts/' + re.escape(payload['id']) + r'/r(?!000000)[0-9]{6}\.md', path):
        raise ValueError('Unexpected revision result')
    if command == 'review' and (set(result) != {'revision', 'verified'} or not isinstance(result['verified'], list)):
        raise ValueError('Unexpected review result')
    return [path]


def load(store, path):
    raw = store.read(path)
    if len(raw) > 8000000:
        raise ValueError('Receipt is too large')
    value = json.loads(raw, parse_constant=lambda _: None)
    if raw != encoded(value):
        raise ValueError('Receipt is not canonical JSON')
    return value


def execute(store, request_id, command, payload, precondition, mutate):
    """All payload reads and this function run under the same caller-held lock."""
    if request_id is None:
        precondition()
        return mutate()
    identifier(request_id)
    folder = f'{ROOT}/{request_id}'
    fingerprint = digest(encoded({'command': command, 'payload': payload}))
    intent = {'version': 1, 'command': command, 'fingerprint': fingerprint}
    recovery = WikiError(f'Request {request_id} may be incomplete or corrupt; inspect {folder} and bundle artifacts; do not blindly retry',
                         'recovery_required')
    try:
        try:
            with store.parent(folder) as (fd, name):
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            info = None
        if info is not None:
            if not stat.S_ISDIR(info.st_mode):
                raise recovery
            previous = load(store, folder + '/intent.json')
            if (not isinstance(previous, dict) or set(previous) != set(intent)
                    or type(previous['version']) is not int or previous['version'] != 1
                    or previous['command'] not in ('capture', 'curate', 'review')
                    or not isinstance(previous['fingerprint'], str)
                    or not re.fullmatch(r'[0-9a-f]{64}', previous['fingerprint'])):
                raise recovery
            if previous != intent:
                raise WikiError('Request ID already belongs to a different payload', 'request_conflict')
            completed = load(store, folder + '/result.json')
            if not isinstance(completed, dict) or set(completed) != {'intent', 'result', 'artifacts', 'checksum'} or encoded(completed['intent']) != encoded(intent):
                raise recovery
            checksum = completed.pop('checksum')
            if checksum != digest(encoded(completed)):
                raise recovery
            paths = effect_paths(command, payload, completed['result'])
            if completed['artifacts'] != {p: digest(store.read(p)) for p in paths}:
                raise recovery
            return completed['result']
    except WikiError as exc:
        if exc.code == 'request_conflict':
            raise
        raise recovery from exc
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise recovery from exc

    precondition()
    try:
        with store.parent(folder, create=True) as (fd, name):
            os.mkdir(name, dir_fd=fd)
        store.create(folder + '/intent.json', encoded(intent))
        sync_receipt(store, folder)
        result = mutate()
        result = json.loads(encoded(result))
        artifacts = {p: digest(store.read(p)) for p in effect_paths(command, payload, result)}
        record = {'intent': intent, 'result': result, 'artifacts': artifacts}
        completed = encoded({**record, 'checksum': digest(encoded(record))})
        if len(completed) > 8000000:
            raise ValueError('Receipt result is too large')
        store.create(folder + '/result.json', completed)
        sync_receipt(store, folder)
        return result
    except Exception as exc:
        raise recovery from exc
