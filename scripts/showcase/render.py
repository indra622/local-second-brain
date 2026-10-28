"""Render selected real CLI lines with ImageMagick. Full captures stay unchanged.
Run generate.py first. --frames keeps render inputs outside the public site.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--frames', type=Path, required=True)
args = parser.parse_args()
args.frames.mkdir(parents=True, exist_ok=True)
data = json.loads((ROOT / 'site/data/sample.json').read_text())
assets = ROOT / 'site/assets'
frames = data['frames']
# Selection is derived from complete stdout; captions are separate editorial text.
save = next(f for f in frames if f['command'].startswith('second-brain curate '))
find = next(f for f in frames if f['command'].startswith('second-brain search '))
read = next(f for f in frames if f['command'].startswith('second-brain show '))
diff = next(f for f in frames if f['command'].startswith('second-brain diff '))
selections = [
    ('Save a note', save, save['output'].splitlines()),
    ('Find it', find, [line for line in find['output'].splitlines() if line and not line.lstrip().startswith('#')]),
    ('Read it', read, [line for line in read['output'].splitlines() if line and not line.lstrip().startswith('Metadata:')]),
    ('Compare changes', diff, [line for line in diff['output'].splitlines() if line.startswith(('--- ', '+++ ', '-Send ', '+Send '))]),
]
images, evidence = [], []
for i, (caption, frame, selected) in enumerate(selections):
    assert all(line in frame['output'].splitlines() for line in selected)
    lines = [wrapped for line in selected for wrapped in (textwrap.wrap(line, width=55, replace_whitespace=False, drop_whitespace=False) or [''])]
    assert len(lines) <= 10, len(lines)
    txt = args.frames / f'excerpt-{i}.txt'
    txt.write_text('\n'.join(lines))
    path = args.frames / f'excerpt-{i}.png'
    subprocess.run(['magick','-size','960x560','xc:#f5f7f7','-fill','#182b2b','-font','Menlo-Regular','-pointsize','27','-interline-spacing','6','-annotate','+32+172','@'+str(txt),'-fill','#176e69','-font','Menlo-Bold','-pointsize','21','-annotate','+32+42','Local Second Brain','-font','Helvetica-Bold','-pointsize','32','-annotate','+32+104',caption,'-font','Menlo-Regular','-pointsize','16','-annotate','+32+514','Selected actual CLI output; timing edited.','-annotate','+32+540','Synthetic inputs. Full commands and transcript linked beside replay.',str(path)],check=True)
    subprocess.run(['magick',str(path),'(',str(assets / 'logo.png'),'-resize','90x90',')','-gravity','northeast','-geometry','+5+0','-composite',str(path)],check=True)
    evidence.append({'caption': caption, 'command':frame['command'], 'selectedLines':selected})
    images.append(path)
subprocess.run(['magick',str(images[2]),str(assets / 'cli-poster.png')],check=True)
cmd = ['magick']
for path, delay in zip(images, [300,300,400,500], strict=True):
    cmd.extend(['-delay',str(delay),str(path)])
cmd.extend(['-loop','1','-layers','Optimize',str(assets / 'cli-demo.gif')])
subprocess.run(cmd,check=True)
(ROOT / 'site/data/replay-selection.json').write_text(json.dumps(evidence,indent=2)+'\n')
manifest = {str(path.relative_to(ROOT / 'site')): hashlib.sha256(path.read_bytes()).hexdigest() for path in [ROOT / 'site/data/sample.json', ROOT / 'site/data/transcript.txt', ROOT / 'site/data/replay-selection.json', assets / 'cli-demo.gif', assets / 'cli-poster.png']}
(ROOT / 'site/data/replay-sha256.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('Rendered 4 validated actual-output excerpts, 15 seconds, single playback, 960x560.')
