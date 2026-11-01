"""Verify current public sample/replay binding, active/archive assets and links.
Run from checkout against approved artifacts; generation is separate. No new dependencies.
"""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

import os
ROOT = Path(os.environ.get('SHOWCASE_ROOT', Path(__file__).resolve().parents[2]))
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
    new = (ROOT / name).read_text()
    for target in re.findall(r'<img[^>]+src="([^\"]+)"',new) + re.findall(r'\]\((site/[^)]+)\)',new):
        assert (ROOT / target).exists(), target
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
# Current player/source versions are an enduring contract, not a past PR diff.
for lang in ('en', 'ko'):
    for suffix, folder in (('mp4','assets'),('jpg','assets'),('vtt','data'),('txt','data')):
        target = f'{folder}/agent-report-v2-{lang}.{suffix}'
        assert target in site_html + site_js or f'{folder}/agent-report-v2-${{scenarioLocale}}.{suffix}' in site_js, target
assert 'report-scenario-v1-' not in site_html + site_js
for relative, info in json.loads((ROOT / 'scripts/showcase/preserved-assets.json').read_text()).items():
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == info['sha256'], relative
manifest = json.loads((ROOT / 'archive/showcase/manifest.json').read_text())
assert len(manifest['files']) == 11 and manifest['total_bytes'] == 1407122
for item in manifest['files']:
    archived = ROOT / item['archive_path']
    assert not (ROOT / item['old_path']).exists(), item['old_path']
    assert not archived.is_relative_to(SITE)
    assert archived.stat().st_size == item['bytes']
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == item['sha256']
    assert archived.stat().st_mode & 0o111 == int(item['mode'], 8) & 0o111
archived_hashes = {item['sha256'] for item in manifest['files']}
assert not any(hashlib.sha256(p.read_bytes()).hexdigest() in archived_hashes for p in SITE.rglob('*') if p.is_file()), 'Inactive bytes in Pages payload'
sample = json.loads((SITE / 'data/sample.json').read_text())
transcript = (SITE / 'data/transcript.txt').read_text()
for frame in sample['frames']:
    assert '$ '+frame['command']+'\n'+frame['output'] in transcript
for path,digest in json.loads((SITE / 'data/replay-sha256.json').read_text()).items():
    assert hashlib.sha256((SITE / path).read_bytes()).hexdigest() == digest,path
for excerpt in json.loads((SITE / 'data/replay-selection.json').read_text()):
    original = next(frame for frame in sample['frames'] if frame['command'] == excerpt['command'])
    assert all(line in original['output'].splitlines() for line in excerpt['selectedLines'])
fixture_bytes = {p.read_bytes() for p in (ROOT / 'scripts/showcase/fixtures').glob('*.txt')}
for note in sample['notes']:
    for source in note['sources'].values():
        blob = source['text'].encode('utf-8')
        assert blob in fixture_bytes, 'Sample source differs from synthetic fixture'
        assert hashlib.sha256(blob).hexdigest() == source['sha256'], 'Source proof hash'
assert sample['preservedSha256']['source'] == sample['notes'][0]['sources']['report-memo-1']['sha256']
assert sample['check'] == {'invalid':[],'warnings':[],'stale':[],'concepts':3}
report = next(n for n in sample['notes'] if n['id'] == 'report-rules')
assert [r['current'] for r in report['revisions']] == [False, True]
assert 'Friday' in report['revisions'][0]['body'] and 'Thursday' in report['revisions'][1]['body']
assert all(r['trust'] == 'unverified' and r['status'] == 'draft' for r in report['revisions'])
assert sample['search'] and all(hit['current'] for hit in sample['search'])
assert any('+Send' in f['output'] and 'Thursday' in f['output'] for f in sample['frames'] if f['command'].startswith('second-brain diff '))
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

print('PASS: current v2 links/version, approved active/source hashes, eleven archived assets, EN/KO outcomes, replay proof/transcript binding, clean CLI check, contrast and GIF budget.')
