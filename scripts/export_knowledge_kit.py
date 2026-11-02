"""Copy a product-only agent packet to a new external directory; never run an agent."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = tuple('knowledge-kit/' + name for name in (
    'START.md', 'START.ko.md', 'practice.md', 'practice.ko.md',
    'navigation.md', 'navigation.ko.md', 'landing-fragment.md', 'landing-fragment.ko.md',
    'note-body.md', 'note-body.ko.md', 'profile.example.json', 'profile.example.ko.json'))
REFERENCES = ('LICENSE', 'workflows/AGENT-WORKFLOW.md', 'workflows/AGENT-WORKFLOW.ko.md',
              'docs/reference.md', 'docs/reference.ko.md', 'docs/review-contract.md',
              'docs/work-context.md', 'docs/work-context.ko.md', 'docs/graph.md', 'docs/graph.ko.md',
              'docs/health.md', 'docs/health.ko.md',
              'docs/retrieval-evaluation.md', 'docs/retrieval-evaluation.ko.md')


def reference_links(text, source):
    def replace(match):
        target = urlsplit(match[2])
        if target.scheme or not target.path:
            return match[0]
        resolved = (ROOT / source).parent.joinpath(unquote(target.path)).resolve()
        allowed = {ROOT / name for name in PRODUCT + REFERENCES}
        return match[0] if resolved in allowed else match[1] + ' (optional reference not bundled)'
    # Only navigation prose is rewritten; literal code examples stay unchanged.
    chunks = re.split(r'(```.*?```)', text, flags=re.S)
    for i in range(0, len(chunks), 2):
        spans = re.split(r'(`[^`\n]*`)', chunks[i])
        for j in range(0, len(spans), 2):
            spans[j] = re.sub(r'(\[[^\]\n]+\])\(([^)\n]+)\)', replace, spans[j])
        chunks[i] = ''.join(spans)
    return ''.join(chunks)


def export(output):
    if not output.is_absolute():
        raise ValueError('Output must be an absolute new external directory')
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; no overwrite or merge')
    destination = output.resolve()
    if destination.is_relative_to(ROOT) or not destination.parent.is_dir():
        raise ValueError('Choose an external destination with an existing parent')
    prepared = []
    for name in PRODUCT + REFERENCES:
        source = ROOT / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Packet source must be a regular repository file: ' + name)
        original = source.read_bytes()
        data = reference_links(original.decode('utf-8'), name).encode('utf-8') if name in REFERENCES else original
        prepared.append((name, original, data))
    destination.mkdir()
    manifest = {'packet_version': 1, 'entry_en': 'knowledge-kit/START.md',
                'entry_ko': 'knowledge-kit/START.ko.md', 'files': []}
    for name, original, data in prepared:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest['files'].append({'path': name, 'source_sha256': hashlib.sha256(original).hexdigest(),
                                  'export_sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    (destination / 'packet-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = export(args.output)
    except (ValueError, OSError) as exc:
        parser.exit(2, 'Packet export failed (a new partial directory may require inspection): ' + str(exc) + '\n')
    print(json.dumps({'output': str(args.output), 'files': len(manifest['files']),
                      'entry_en': manifest['entry_en'], 'entry_ko': manifest['entry_ko']}))


if __name__ == '__main__':
    main()
