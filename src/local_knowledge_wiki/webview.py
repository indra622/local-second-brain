"""Explicit loopback viewer. Never takes a writer lock or serves arbitrary files."""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
from pathlib import Path

from . import annotations
from .format import local_target
from .graph import markdown_links
from .reading import REVISION_PATH, read_note
from .storage import Store, WikiError, current_index, identifier

FILE_BYTES = 512 * 1024
TOTAL_BYTES = 8 * 1024 * 1024
RESPONSE_BYTES = 12 * 1024 * 1024
ENTRY_LIMIT = 512
NOTE_LIMIT = 100
REVISION_LIMIT = 256
SOURCE_LIMIT = 128
LINK_LIMIT = 256


def encoded(value):
    return json.dumps(value, ensure_ascii=False, default=str, allow_nan=False).encode('utf-8')


def bounded_metadata(value):
    """Charge repeated alias visits before allocation; preserve reader scalar spelling."""
    active = set()
    visits = 0
    size = 0

    def convert(item, depth=0):
        nonlocal visits, size
        visits += 1
        if visits > 4096 or depth > 16:
            raise WikiError('Viewer metadata traversal limit exceeded', 'input_too_large')
        if isinstance(item, (dict, list, set)):
            identity = id(item)
            if identity in active:
                raise WikiError('Cyclic viewer metadata')
            active.add(identity)
            size += 2
            try:
                if isinstance(item, dict):
                    result = {}
                    for key, child in item.items():
                        key = convert(key if isinstance(key, str) else str(key), depth + 1)
                        if key in result:
                            raise WikiError('Viewer metadata keys collide')
                        result[key] = convert(child, depth + 1)
                elif isinstance(item, list):
                    result = [convert(child, depth + 1) for child in item]
                else:
                    for child in item:
                        convert(child, depth + 1)
                    result = str(item)
            finally:
                active.remove(identity)
            return result
        if not isinstance(item, (str, int, float, bool, type(None))):
            item = str(item)
        size += len(encoded(item)) + 2
        if size > FILE_BYTES:
            raise WikiError('Viewer metadata output limit exceeded', 'input_too_large')
        return item

    return convert(value)


def root_identity(root):
    path = Path(os.path.abspath(root))
    if path.resolve(strict=True) != path:
        raise WikiError('Viewer root must not contain symlinks', 'unsafe_path')
    with Store(path) as store:
        info = os.fstat(store.fd)
    return path, (info.st_dev, info.st_ino)


class Scan:
    def __init__(self, store):
        self.store = store
        self.seen = {}
        self.missing = set()
        self.used = 0
        self.directories = {}

    def read(self, path):
        if path in self.seen:
            return self.seen[path]
        try:
            raw = self.store.read(path, max_bytes=min(FILE_BYTES, TOTAL_BYTES - self.used))
        except FileNotFoundError:
            self.missing.add(path)
            raise
        self.used += len(raw)
        self.seen[path] = raw
        return raw

    def directory(self, path):
        # Open known directories only; never walk receipts, app folders or neighbors.
        with self.store.parent(path + '/entry') as (fd, _):
            names = []
            with os.scandir(fd) as entries:
                for entry in entries:
                    if len(names) >= ENTRY_LIMIT:
                        raise WikiError('Viewer directory entry limit exceeded', 'input_too_large')
                    if entry.is_symlink():
                        raise WikiError('Symlink in selected concept directory', 'unsafe_path')
                    names.append(entry.name)
        names.sort()
        self.directories[path] = names
        return names

    def stable(self):
        for path, names in list(self.directories.items()):
            if self.directory(path) != names:
                raise WikiError('History moved during refresh; refresh again')
        for path, raw in self.seen.items():
            if self.store.read(path, max_bytes=FILE_BYTES) != raw:
                raise WikiError('Files moved during refresh; refresh again')
        for path in self.missing:
            try:
                self.store.read(path, max_bytes=FILE_BYTES)
            except FileNotFoundError:
                continue
            raise WikiError('Missing file appeared during refresh; refresh again')


def source(scan, source_id):
    identifier(source_id)
    result = {'id': source_id, 'state': 'unavailable', 'text': None, 'provenance': None}
    try:
        raw = scan.read(f'sources/{source_id}/content.raw')
        result.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        try:
            result['text'] = raw.decode('utf-8')
        except UnicodeError:
            result['state'] = 'non-utf8'
        else:
            result['state'] = 'available'
        try:
            provenance = json.loads(scan.read(f'sources/{source_id}/provenance.json'))
            if not isinstance(provenance, dict):
                raise ValueError('Provenance must be an object')
            result['provenance'] = provenance
            result['hash_matches_declaration'] = provenance.get('sha256') == result['sha256']
        except (FileNotFoundError, ValueError, UnicodeError):
            result['provenance_error'] = '출처 메타데이터를 확인할 수 없습니다.'
    except FileNotFoundError:
        result['error'] = '보존 원문을 찾지 못했습니다.'
    return result


def related(note, current, loaded):
    result = []
    for resource, line in markdown_links(note['body']):
        if len(result) >= LINK_LIMIT:
            return result, True
        item = {'resource': resource, 'line': line, 'kind': '본문 링크', 'state': 'unchecked'}
        try:
            target = local_target(note['path'], resource)
        except (WikiError, ValueError):
            item['state'] = 'unsafe'
        else:
            if target:
                item['path'] = target
                if REVISION_PATH.fullmatch(target):
                    item['state'] = 'available' if target in loaded else 'unavailable-or-out-of-scope'
        result.append(item)
    root = note['metadata'].get(annotations.KEY)
    if root is not None:
        try:
            errors = {}
            annotations.stored_root(root, note['id'], section_errors=errors,
                                    sources=note['metadata'].get('sources'))
            if errors:
                note['metadata_errors'].extend('annotation: ' + str(k) for k in errors)
            if 'relations' not in errors:
                for relation in root.get('relations', {}).get('data', {}).get('items', []):
                    if len(result) >= LINK_LIMIT:
                        return result, True
                    target = relation['target']
                    path = (f"concepts/{target['id']}/{target['revision']}.md" if 'revision' in target
                            else current.get(target['id']))
                    result.append({'kind': relation['type'], 'path': path,
                                   'resource': target, 'evidence': relation['evidence'],
                                   'state': 'available' if path in loaded else 'unavailable-or-out-of-scope'})
        except (WikiError, TypeError, ValueError, RecursionError):
            note['metadata_errors'].append('확장 메타데이터가 잘못되었거나 지원 범위 밖입니다.')
    return result, False


def snapshot(root, identity):
    started = datetime.now(timezone.utc)
    path, observed = root_identity(root)
    if observed != identity:
        raise WikiError('Selected bundle root moved; restart viewer')
    with Store(path) as store:
        info = os.fstat(store.fd)
        if (info.st_dev, info.st_ino) != identity:
            raise WikiError('Selected bundle root changed')
        scan = Scan(store)
        current = current_index(scan.read('index.md').decode('utf-8'))[0]
        if len(current) > NOTE_LIMIT:
            raise WikiError('Viewer supports at most 100 indexed concepts per scan', 'input_too_large')
        notes, histories, sources, diagnostics = {}, {}, {}, []
        for concept_id, selected in current.items():
            try:
                names = scan.directory(f'concepts/{concept_id}')
            except FileNotFoundError:
                names = []
            paths = [f'concepts/{concept_id}/{name}' for name in names
                     if REVISION_PATH.fullmatch(f'concepts/{concept_id}/{name}') and name != 'r000000.md']
            if len(notes) + len(paths) > REVISION_LIMIT:
                raise WikiError('Viewer revision limit exceeded', 'input_too_large')
            histories[concept_id] = paths
            if selected not in paths:
                diagnostics.append({'path': selected, 'state': 'missing-current'})
            for revision in paths:
                try:
                    note, _ = read_note(scan, revision, started, current)
                    note['metadata'] = bounded_metadata(note['metadata'])
                    note.update(id=concept_id, sha256=hashlib.sha256(scan.read(revision)).hexdigest())
                    note['status'] = note['status'] if not note['metadata_errors'] else 'unknown'
                    if note['metadata_errors']:
                        note['stale'] = None
                    declared = note['metadata'].get('sources', [])
                    note['source_ids'] = []
                    note['source_refs'] = []
                    if isinstance(declared, list):
                        for item in declared:
                            if not isinstance(item, dict) or not isinstance(item.get('id'), str):
                                note['source_refs'].append({'declaration': item, 'state': 'unsupported-or-unknown'})
                                continue
                            sid = item['id']
                            try:
                                identifier(sid)
                            except WikiError:
                                note['source_refs'].append({'declaration': item, 'state': 'unsafe-id'})
                                continue
                            try:
                                target = local_target(revision, item.get('resource', '')) if isinstance(item.get('resource'), str) else None
                            except (WikiError, ValueError):
                                target = None
                            if target != f'sources/{sid}/content.raw':
                                note['source_refs'].append({'declaration': item, 'state': 'unsupported-or-mismatched-binding'})
                                continue
                            note['source_refs'].append({'declaration': item, 'state': 'canonical-binding'})
                            if sid not in sources:
                                if len(sources) >= SOURCE_LIMIT:
                                    raise WikiError('Viewer source limit exceeded', 'input_too_large')
                                sources[sid] = source(scan, sid)
                            note['source_ids'].append(sid)
                    notes[revision] = note
                except FileNotFoundError:
                    diagnostics.append({'path': revision, 'state': 'missing-during-scan'})
        for note in notes.values():
            note['related'], partial = related(note, current, notes)
            note['related_partial'] = partial
        scan.stable()
        if root_identity(path)[1] != identity:
            raise WikiError('Selected bundle root moved during refresh')
        result = {'bundle': path.name, 'scanned_at': started.isoformat(),
                  'completed_at': datetime.now(timezone.utc).isoformat(),
                  'consistency': 'best-effort, rechecked bytes; not an atomic transaction',
                  'current': current, 'notes': notes, 'histories': histories, 'sources': sources,
                  'diagnostics': diagnostics, 'partial': bool(diagnostics),
                  'limits': {'concepts': NOTE_LIMIT, 'revisions': REVISION_LIMIT,
                             'sources': SOURCE_LIMIT, 'file_bytes': FILE_BYTES, 'total_bytes': TOTAL_BYTES}}
        payload = encoded(result)
        if len(payload) > RESPONSE_BYTES:
            raise WikiError('Viewer response limit exceeded', 'input_too_large')
        return payload


class ViewerServer(HTTPServer):
    allow_reuse_address = False

    def __init__(self, root, port=0):
        self.root, self.identity = root_identity(root)
        super().__init__(('127.0.0.1', port), ViewerHandler)
        self.authority = f'127.0.0.1:{self.server_port}'
        self.origin = 'http://' + self.authority
        self.timeout = 1

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address


class ViewerHandler(BaseHTTPRequestHandler):
    server_version = 'LocalSecondBrainViewer'

    def log_message(self, *args):
        pass

    def reply(self, code, data=b'', content_type='text/plain; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(data)

    def allowed(self):
        return (self.headers.get_all('Host') == [self.server.authority]
                and self.headers.get_all('Origin', []) in ([], [self.server.origin])
                and self.headers.get('Sec-Fetch-Site', 'none') in ('none', 'same-origin'))

    def do_GET(self):
        if len(self.path) > 2048:
            return self.reply(414)
        if not self.allowed():
            return self.reply(403)
        assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                  '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path in assets:
            name, kind = assets[self.path]
            return self.reply(200, files('local_knowledge_wiki').joinpath('web', name).read_bytes(), kind)
        if self.path != '/api/snapshot':
            return self.reply(404)
        try:
            payload = snapshot(self.server.root, self.server.identity)
        except (WikiError, OSError, UnicodeError, ValueError, TypeError, RecursionError):
            return self.reply(503, encoded({'error': '읽기 실패: 번들 변경, 경로 안전성, 형식 또는 읽기 한도를 확인한 뒤 다시 시도하세요. 마지막 성공 화면은 유지됩니다.'}), 'application/json; charset=utf-8')
        self.reply(200, payload, 'application/json; charset=utf-8')

    def do_POST(self):
        self.reply(405)

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST
    do_OPTIONS = do_POST
    do_HEAD = do_POST


def serve(root, port):
    if not 0 <= port <= 65535:
        raise WikiError('Port must be between 0 and 65535')
    with ViewerServer(root, port) as server:
        print(f'Read-only viewer: {server.origin}/ (Ctrl-C to stop)', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
