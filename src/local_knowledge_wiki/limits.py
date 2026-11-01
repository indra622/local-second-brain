"""Per-file byte budgets, independent of recall's output character budget."""

from .errors import WikiError


SOURCE_BYTES = 256 * 1024 * 1024
BODY_BYTES = 16 * 1024 * 1024
METADATA_BYTES = 8000000
INDEX_BYTES = 8000000
RECEIPT_BYTES = 8000000
REVISION_BYTES = BODY_BYTES + METADATA_BYTES + 10


def check_size(size, limit, label):
    if size > limit:
        raise WikiError(f'{label} exceeds {limit} byte input limit', 'input_too_large')


def file_limit(path):
    if path.startswith('.lkw-requests/'):
        return RECEIPT_BYTES
    if path.endswith('/provenance.json'):
        return METADATA_BYTES
    if path == 'index.md':
        return INDEX_BYTES
    if path.endswith('.md'):
        return REVISION_BYTES
    return SOURCE_BYTES


def bounded_read(stream, limit, label):
    # A size check alone misses files that grow after fstat. Never request an
    # unbounded read; the extra byte distinguishes an exact fit from overflow.
    check_size(0, limit, label)
    data = bytearray()
    while len(data) <= limit:
        block = stream.read(min(1024 * 1024, limit + 1 - len(data)))
        if not block:
            return bytes(data)
        data.extend(block)
        check_size(len(data), limit, label)
    raise AssertionError('unreachable')


def bounded_markdown_read(stream, limit, label):
    first = stream.readline(min(limit, METADATA_BYTES) + 1)
    check_size(len(first), limit, label)
    if first not in (b'---\n', b'---\r\n'):
        rest = bounded_read(stream, limit - len(first), label)
        return first + rest
    header = bytearray(first)
    used = 0
    while True:
        line = stream.readline(METADATA_BYTES - used + 5)
        if line in (b'---\n', b'---\r\n', b'---'):
            header.extend(line)
            check_size(len(header), limit, label)
            break
        used += len(line)
        check_size(used, METADATA_BYTES, 'frontmatter')
        header.extend(line)
        check_size(len(header), limit, label)
        if not line:
            return bytes(header)
    body = bounded_read(stream, min(BODY_BYTES, limit - len(header)), 'body')
    return bytes(header) + body
