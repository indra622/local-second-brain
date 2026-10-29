"""Bounded, read-only storage inventory. No repair or replay eligibility claims."""

import hashlib
import json
import os
import re
import stat
from contextlib import ExitStack

from .errors import WikiError, error_code
from .reading import REVISION_PATH
from .requests import ROOT, digest, effect_paths, encoded
from .storage import LockCapabilityError, STAGE_PATTERN, Store, current_index


DETAIL_LIMIT = 100
ENTRY_LIMIT = 10000
DEPTH_LIMIT = 16
READ_LIMIT = 8000000
HASH_LIMIT = 64000000
RECEIPT_LIMIT = 100
ID = r'[a-z0-9][a-z0-9-]{0,63}'


def valid_intent(value):
    return (isinstance(value, dict) and set(value) == {'version', 'command', 'fingerprint'}
            and type(value['version']) is int and value['version'] == 1
            and value['command'] in ('capture', 'curate', 'review')
            and isinstance(value['fingerprint'], str)
            and re.fullmatch(r'[0-9a-f]{64}', value['fingerprint']) is not None)


def receipt_paths(intent, completed):
    if (not isinstance(completed, dict) or set(completed) != {'intent', 'result', 'artifacts', 'checksum'}
            or encoded(completed['intent']) != encoded(intent)):
        raise ValueError('Invalid completed receipt schema')
    record = {k: v for k, v in completed.items() if k != 'checksum'}
    if completed['checksum'] != digest(encoded(record)):
        raise ValueError('Receipt checksum mismatch')
    command, result = intent['command'], completed['result']
    path = result.get('revision') if command == 'review' and isinstance(result, dict) else result
    pattern = rf'sources/({ID})/content\.raw' if command == 'capture' else rf'concepts/({ID})/r(?!000000)[0-9]{{6}}\.md'
    match = re.fullmatch(pattern, path) if isinstance(path, str) else None
    if not match:
        raise ValueError('Unsafe or invalid receipt result path')
    paths = effect_paths(command, {'id': match[1]}, result)
    artifacts = completed['artifacts']
    if (not isinstance(artifacts, dict) or set(artifacts) != set(paths)
            or any(not isinstance(v, str) or re.fullmatch(r'[0-9a-f]{64}', v) is None for v in artifacts.values())):
        raise ValueError('Unsafe or invalid receipt effect paths/digests')
    return paths


def read_receipt(store, path):
    raw = store.read(path, max_bytes=READ_LIMIT)
    value = json.loads(raw, parse_constant=lambda _: None)
    if raw != encoded(value):
        raise ValueError('Noncanonical receipt JSON')
    return value


def hash_effect(store, path, max_bytes=HASH_LIMIT):
    with store.parent(path) as (fd, name):
        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
        with os.fdopen(handle, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise WikiError('Nonregular receipt effect', 'unsafe_path')
            if info.st_size > max_bytes:
                return None, 0
            value = hashlib.sha256()
            remaining = max_bytes + 1
            used = 0
            while remaining:
                block = stream.read(min(1048576, remaining))
                if not block:
                    return value.hexdigest(), used
                value.update(block)
                remaining -= len(block)
                used += len(block)
            return None, used


def inspect_storage(root):
    report = {'consistency': 'best_effort', 'lock': {},
              'limits': {'details_per_section': DETAIL_LIMIT, 'entries': ENTRY_LIMIT,
                         'depth': DEPTH_LIMIT, 'receipt_bytes': READ_LIMIT,
                         'receipts_checked': RECEIPT_LIMIT, 'effect_hash_bytes': HASH_LIMIT,
                         'total_effect_hash_bytes': HASH_LIMIT * 2},
              'index': {'state': 'unavailable', 'missing_current': 0, 'targets_unavailable': 0},
              'revisions': {'total': 0, 'current': None, 'non_current': None,
                            'non_current_with_completion_evidence': 0, 'unclassified_non_current': None},
              'receipts': {'total': 0, 'checked': 0, 'states': {}}, 'staging': {'total': 0},
              'details': {'missing_current': [], 'revisions': [], 'receipts': [], 'staging': [], 'diagnostics': []},
              'omitted': {'missing_current': 0, 'revisions': 0, 'receipts': 0, 'staging': 0, 'diagnostics': 0},
              'scan': {'visited': 0, 'complete': True},
              'guidance': 'Inventory only. Non-current includes ordinary history; no orphan inference. Never infer safe replay/deletion from this report. Pending state can be an active write.'}

    def detail(section, item):
        if len(report['details'][section]) >= DETAIL_LIMIT:
            report['omitted'][section] += 1
            return
        clipped = {k: (v[:240] if isinstance(v, str) else v) for k, v in item.items()}
        if any(isinstance(v, str) and len(v) > 240 for v in item.values()):
            clipped['text_truncated'] = True
        report['details'][section].append(clipped)

    def diagnostic(path, exc):
        detail('diagnostics', {'path': path, 'code': error_code(exc), 'message': str(exc)})

    with Store(root) as store, ExitStack() as stack:
        try:
            handle = stack.enter_context(store.lock(shared=True, create=False))
            info = os.fstat(handle)
            report['lock'] = {'state': 'recognized_available', 'inode': info.st_ino, 'device': info.st_dev}
            report['consistency'] = 'shared_lock_held'
        except FileNotFoundError:
            report['lock'] = {'state': 'absent'}
        except (OSError, WikiError) as exc:
            state = {'locked': 'recognized_busy', 'recovery_required': 'legacy_or_unknown',
                     'unsafe_path': 'unsafe'}.get(error_code(exc), 'unavailable')
            if isinstance(exc, LockCapabilityError):
                state = 'unavailable'
            report['lock'] = {'state': state}
            diagnostic('.lkw.lock', exc)
        try:
            current = current_index(store.read('index.md', max_bytes=READ_LIMIT).decode('utf-8'))[0]
            report['index'].update(state='valid', entries=len(current))
        except (OSError, WikiError, UnicodeError) as exc:
            current = None
            report['index']['state'] = 'missing' if isinstance(exc, FileNotFoundError) else 'invalid_or_unavailable'
            diagnostic('index.md', exc)
        if current is not None:
            report['index']['targets_unchecked'] = max(0, len(current) - ENTRY_LIMIT)
            for path in list(current.values())[:ENTRY_LIMIT]:
                try:
                    with store.parent(path) as (fd, name):
                        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                        if not stat.S_ISREG(info.st_mode):
                            raise WikiError('Current target is not a regular file', 'unsafe_path')
                except FileNotFoundError:
                    report['index']['missing_current'] += 1
                    detail('missing_current', {'path': path, 'state': 'missing'})
                except (OSError, WikiError) as exc:
                    report['index']['targets_unavailable'] += 1
                    diagnostic(path, exc)

        revisions, receipts, completed_revisions = [], [], set()
        hash_remaining = HASH_LIMIT * 2

        def walk(fd, prefix='', depth=0):
            if depth > DEPTH_LIMIT:
                report['scan']['complete'] = False
                diagnostic(prefix, WikiError('Inspection depth limit reached'))
                return
            try:
                with os.scandir(fd) as entries:
                    for entry in entries:
                        if report['scan']['visited'] >= ENTRY_LIMIT:
                            report['scan']['complete'] = False
                            return
                        report['scan']['visited'] += 1
                        name, path = entry.name, prefix + entry.name
                        if name in ('.git', '.obsidian'):
                            continue
                        try:
                            info = entry.stat(follow_symlinks=False)
                            regular = stat.S_ISREG(info.st_mode)
                            directory = stat.S_ISDIR(info.st_mode)
                            if prefix == '' and (name == '.lkw-index.tmp' or STAGE_PATTERN.fullmatch(name)):
                                report['staging']['total'] += 1
                                detail('staging', {'path': path, 'type': 'regular' if regular else 'unsafe', 'bytes': info.st_size,
                                                   'ownership': 'unknown'})
                            if not regular and not directory:
                                diagnostic(path, WikiError('Unsafe inspection entry; not followed', 'unsafe_path'))
                                report['scan']['complete'] = False
                                continue
                            if prefix == ROOT + '/':
                                report['receipts']['total'] += 1
                                if re.fullmatch(ID, name) and directory:
                                    receipts.append(path)
                                else:
                                    diagnostic(path, WikiError('Unexpected receipt namespace entry'))
                                continue
                            if regular and REVISION_PATH.fullmatch(path) and not path.endswith('/r000000.md'):
                                revisions.append(path)
                            if directory:
                                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                                try:
                                    walk(child, path + '/', depth + 1)
                                finally:
                                    os.close(child)
                        except (OSError, WikiError) as exc:
                            diagnostic(path, exc)
                            report['scan']['complete'] = False
            except OSError as exc:
                diagnostic(prefix, exc)
                report['scan']['complete'] = False

        walk(store.fd)
        for folder in sorted(receipts)[:RECEIPT_LIMIT]:
            state = 'corrupt'
            paths = []
            try:
                try:
                    intent = read_receipt(store, folder + '/intent.json')
                except FileNotFoundError:
                    state = 'incomplete'
                    raise
                if not valid_intent(intent):
                    raise ValueError('Invalid receipt intent schema')
                try:
                    completed = read_receipt(store, folder + '/result.json')
                except FileNotFoundError:
                    state = 'pending'
                    raise
                paths = receipt_paths(intent, completed)
                state = 'self_consistent'
                for path in paths:
                    if hash_remaining > 1:
                        observed, used = hash_effect(store, path, min(HASH_LIMIT, hash_remaining - 1))
                        hash_remaining -= used
                    else:
                        observed = None
                    if observed is None:
                        state = 'effects_unchecked'
                    elif observed != completed['artifacts'][path]:
                        raise ValueError('Receipt effect digest mismatch')
                if state == 'self_consistent':
                    completed_revisions.update(path for path in paths if REVISION_PATH.fullmatch(path))
            except (OSError, WikiError, ValueError, TypeError, KeyError, RecursionError) as exc:
                if state not in ('pending', 'incomplete'):
                    state = 'corrupt'
                diagnostic(folder, exc)
            report['receipts']['checked'] += 1
            counts = report['receipts']['states']
            counts[state] = counts.get(state, 0) + 1
            detail('receipts', {'path': folder, 'state': state, 'replay_eligibility': 'not_established'})
        unchecked = len(receipts) - report['receipts']['checked']
        report['receipts']['unexpected_entries'] = report['receipts']['total'] - len(receipts)
        report['receipts']['unchecked'] = unchecked
        report['omitted']['receipts'] += unchecked
        report['revisions']['total'] = len(revisions)
        if current is not None:
            selected = set(current.values())
            non_current = set(revisions) - selected
            observed = len(non_current & completed_revisions)
            report['revisions'].update(current=len(set(revisions) & selected), non_current=len(non_current),
                                       non_current_with_completion_evidence=observed,
                                       unclassified_non_current=len(non_current) - observed)
        for path in sorted(revisions):
            detail('revisions', {'path': path, 'current': None if current is None else path in current.values(),
                                  'completion_evidence': path in completed_revisions})
        for values in report['details'].values():
            values.sort(key=lambda item: (item.get('path', ''), item.get('message', '')))
        if report['consistency'] == 'shared_lock_held':
            try:
                store.validate_lock(handle)
            except (OSError, WikiError) as exc:
                report['consistency'] = 'best_effort_lock_changed'
                diagnostic('.lkw.lock', exc)
    return report
