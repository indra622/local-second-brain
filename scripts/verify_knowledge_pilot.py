"""Read-only saved-evidence integrity, not a model rerun or qualitative evaluation."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    evidence = root / 'examples/knowledge-practice/observed-v1'
    manifest = json.loads((evidence / 'manifest.json').read_text())
    for item in manifest['files']:
        data = (evidence / item['public_path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256'] and len(data) == item['bytes'], item['public_path']
        assert not any(v in data for v in (b'/Users/', b'/Volumes/', b'/private/', b'/var/folders/')), item['public_path']
    assessment = manifest['assessment']
    raw = (evidence / assessment['public_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == assessment['sha256'] and len(raw) == assessment['bytes']
    held = json.loads((evidence / 'mechanics.json').read_text())
    snapshots = held['snapshots']
    for name, snapshot in snapshots.items():
        expected = held['snapshot_claims'][name]
        assert expected['files'] == len(snapshot)
        assert expected['sha256'] == hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert snapshots['setup-baseline'] == snapshots['q0-after'] and len(snapshots['q0-after']) == 30
    assert snapshots['s4-after'] == snapshots['B-before'] == snapshots['B-after'] and len(snapshots['B-after']) == 74
    old = snapshots['q0-after']
    for stage in held['stages']:
        new = snapshots[stage['stage'] + '-after']
        for path, info in old.items():
            if path.startswith(('product/', 'knowledge/sources/', 'knowledge/concepts/')) or path == 'profile.json':
                assert new[path] == info, path
        assert stage['old_durable_files_unchanged'] and stage['check']['invalid'] == []
        old = new
    for item in manifest['files']:
        if item['public_path'].startswith('knowledge/'):
            assert snapshots['s4-after'][item['public_path']]['sha256'] == item['sha256']
    originals = json.loads((root / 'examples/knowledge-practice/v1/manifest.json').read_text())
    for number in range(1, 5):
        source = evidence / f'knowledge/sources/reading-reflection-{number:02}-source/content.raw'
        target = next(x for x in originals['files'] if x['path'] == f'entry-{number:02}.txt')
        assert hashlib.sha256(source.read_bytes()).hexdigest() == target['sha256']
    index = (evidence / 'knowledge/index.md').read_text()
    block = index.split('<!-- lkw:current:start -->\n')[1].split('<!-- lkw:current:end -->')[0]
    assert 'reading-understanding-self-explanation/r000002.md' in block
    assert 'reading-understanding-self-explanation/r000001.md' not in block
    assert len(re.findall(r'^- \[', block, re.M)) == 3
    assert len(list((evidence / 'knowledge/concepts').glob('*/*.md'))) == 4
    for file in [evidence / row['public_path'] for row in manifest['files'] if row['public_path'].endswith('.md')]:
        for target in re.findall(r'\]\(([^)]+)\)', file.read_text()):
            assert (file.parent / target).resolve().is_relative_to(evidence.resolve())
            assert (file.parent / target).is_file(), (file, target)
    assert len(held['B_commands']) == 3 and all('cat ' in command and 'recall' not in command for command in held['B_commands'])
    return {'exact_artifacts': len(manifest['files']), 'originals': 4, 'revision_files': 4, 'readonly_snapshots': [30, 74]}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
