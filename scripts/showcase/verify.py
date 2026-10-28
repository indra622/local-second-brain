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
    # Only the opening vision block may change from the correction's fixed base.
    old = subprocess.check_output(['git','show',f'3aa15aa:{name}'],cwd=ROOT,text=True)
    new = (ROOT / name).read_text()
    assert len(re.findall(r'```(?:sh|text)\n.*?```',old,re.S)) == 5, name
    assert re.findall(r'```(?:sh|text)\n.*?```',old,re.S) == re.findall(r'```(?:sh|text)\n.*?```',new,re.S), name
    assert re.findall(r'^#+ .*$',old,re.M) == re.findall(r'^#+ .*$',new,re.M), name
    start = '**The Second Brain' if name == 'README.md' else '**우리가 지향'
    lead = '**Spend less time' if name == 'README.md' else '**AI에게 같은 배경'
    intro = 'Local Second Brain stores' if name == 'README.md' else 'Local Second Brain은'
    assert old[:old.index(start)] == new[:new.index(lead)], name
    assert old[old.index(intro):] == new[new.index(intro):], name
    assert 'second-brain-vision' not in new, name
    for target in re.findall(r'<img[^>]+src="([^"]+)"',new):
        assert (ROOT / target).exists(),target
    for target in re.findall(r'\]\((site/[^)]+)\)',new):
        assert (ROOT / target).exists(),target
site_html = (SITE / 'index.html').read_text()
site_js = (SITE / 'app.js').read_text()
# Every outcome sentence has the same wording on the README and site.
outcome_keys = []
for key, english in re.findall(r'<(?:h2|h3|p)[^>]*data-t="([^"]+)"[^>]*>([^<]+)</', site_html):
    if key not in ('outcomeLead','outcomeMechanism','reportHeading','reportOutcome',
                   'resumeHeading','resumeOutcome','recheckHeading','recheckOutcome','outcomeEnd'):
        continue
    outcome_keys.append(key)
    korean = json.loads(re.search(key + r':("[^"\n]+")',site_js).group(1))
    assert english in (ROOT / 'README.md').read_text(), key
    assert korean in (ROOT / 'README.ko.md').read_text(), key
assert len(set(outcome_keys)) == 9
assert 'class="vision"' not in site_html and 'vision-image' not in site_js
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

print('PASS: README prose (except replaced opening vision), headings/sh/text blocks preserved; equivalent EN/KO outcomes, local links, relative site assets, public path/copy scan, replay hashes/transcript binding, clean CLI check, GIF budget.')
