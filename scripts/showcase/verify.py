"""Verify public sample/replay binding, links, and README preservation.
Run from checkout after generator, renderer and browser QA. No new dependencies.
"""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / 'site'


class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('href', 'src'):
            value = attrs.get(key, '')
            if not value or value.startswith(('#','https://','?')):
                continue
            assert not value.startswith('/'), value
            assert (SITE / value.split('?')[0]).exists(), value
        if tag in ('script','link','img'):
            assert not any(v.startswith(('http:', 'https:', '//')) for k,v in attrs.items() if k in ('href','src'))


Links().feed((SITE / 'index.html').read_text())
for name in ('README.md','README.ko.md'):
    old = subprocess.check_output(['git','show',f'origin/main:{name}'],cwd=ROOT,text=True)
    new = (ROOT / name).read_text()
    assert re.findall(r'```(?:sh|text)\n.*?```',old,re.S) == re.findall(r'```(?:sh|text)\n.*?```',new,re.S), name
    assert re.findall(r'^#+ .*$',old,re.M) == re.findall(r'^#+ .*$',new,re.M), name
    # Insertion-only changes preserve every original prose line as a subsequence.
    previous=iter(new.splitlines())
    assert all(any(candidate == line for candidate in previous) for line in old.splitlines()), name
    for target in re.findall(r'\]\((site/[^)]+)\)',new):
        assert (ROOT / target).exists(),target
for file in SITE.rglob('*'):
    if file.suffix in ('.js','.html','.css','.json','.txt','.md'):
        text = file.read_text()
        assert not re.search(r'/Users/|/Volumes/|/private/|/var/folders/|[\u00b7\u2014]',text),file
sample = json.loads((SITE / 'data/sample.json').read_text())
transcript = (SITE / 'data/transcript.txt').read_text()
for frame in sample['frames']:
    assert '$ '+frame['command']+'\n'+frame['output'] in transcript
for path,digest in json.loads((SITE / 'data/replay-sha256.json').read_text()).items():
    assert hashlib.sha256((SITE / path).read_bytes()).hexdigest() == digest,path
for excerpt in json.loads((SITE / 'data/replay-selection.json').read_text()):
    original = next(frame for frame in sample['frames'] if frame['command'] == excerpt['command'])
    assert all(line in original['output'].splitlines() for line in excerpt['selectedLines'])
assert sample['check'] == {'invalid':[],'warnings':[],'stale':[],'concepts':3}
assert (SITE / 'assets/cli-demo.gif').stat().st_size < 4_000_000



def luminance(value):
    rgb = [int(value[i:i+2],16)/255 for i in (1,3,5)]
    rgb = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return sum(a*b for a,b in zip(rgb,[.2126,.7152,.0722]))

for fg,bg,minimum in [('#176e69','#fdfefe',4.5),('#4d6262','#e3efed',4.5),('#87d0c6','#142222',4.5),('#b1c7c5','#263f3d',4.5),('#718686','#e3efed',3),('#789592','#263f3d',3)]:
    low,high = sorted([luminance(fg),luminance(bg)])
    ratio = (high+.05)/(low+.05)
    assert ratio >= minimum, (fg,bg,ratio)
    print(f'Contrast {fg} on {bg}: {ratio:.2f}:1 (minimum {minimum}) PASS')

print('PASS: README original prose/headings/sh/text blocks preserved, local links, relative site assets, public path/copy scan, replay hashes/transcript binding, clean CLI check, GIF budget.')
