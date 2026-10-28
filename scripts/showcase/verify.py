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
    # Fixed pre-vision baseline keeps preservation checks independent of remote updates.
    old = subprocess.check_output(['git','show',f'cb65681:{name}'],cwd=ROOT,text=True)
    new = (ROOT / name).read_text()
    assert re.findall(r'```(?:sh|text)\n.*?```',old,re.S) == re.findall(r'```(?:sh|text)\n.*?```',new,re.S), name
    assert re.findall(r'^#+ .*$',old,re.M) == re.findall(r'^#+ .*$',new,re.M), name
    # The vision replaces only the redundant banner; all other prose is retained.
    banner = {
        'README.md': '[![Local Second Brain introduction and working sample](site/assets/banner.png)](https://indra622.github.io/local-second-brain/)',
        'README.ko.md': '[![Local Second Brain 소개와 실제 예제](site/assets/banner.png)](https://indra622.github.io/local-second-brain/?lang=ko)',
    }[name]
    assert old.splitlines().count(banner) == 1, name
    previous=iter(new.splitlines())
    assert all(any(candidate == line for candidate in previous) for line in old.replace(banner+'\n\n','').splitlines()), name
    assert '<img src="site/assets/second-brain-vision-v01.webp"' in new, name
    assert 'width="1672" height="941"' in new, name
    assert new.index('second-brain-vision-v01.webp') < new.index('```'), name
    for target in re.findall(r'<img[^>]+src="([^"]+)"',new):
        assert (ROOT / target).exists(),target
    for target in re.findall(r'\]\((site/[^)]+)\)',new):
        assert (ROOT / target).exists(),target
site_html = (SITE / 'index.html').read_text()
site_js = (SITE / 'app.js').read_text()
for name, label, description, limit, surface in (
    ('README.md', 'The Second Brain we are building toward',
     'Past sources and decisions connect, so relevant knowledge can support today’s question and the next report or task.',
     'A vision illustration, not a current product screen. Today, you save and search notes with a command-line tool and choose what to give your AI.', site_html),
    ('README.ko.md', '우리가 지향하는 Second Brain',
     '과거에 모은 자료와 내린 결정이 서로 이어지고, 그중 필요한 지식이 오늘의 질문과 다음 보고서나 작업에 쓰이는 모습을 지향합니다.',
     '지향하는 모습을 그린 비전 일러스트입니다. 현재는 사용자가 노트를 저장하고 검색해 AI에게 전달하는 명령줄 도구입니다.', site_js),
):
    for copy in (label, description, limit):
        assert copy in (ROOT / name).read_text() and copy in surface, (name, copy)
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
assert (SITE / 'assets/second-brain-vision-v01.webp').stat().st_size < 500_000



def luminance(value):
    rgb = [int(value[i:i+2],16)/255 for i in (1,3,5)]
    rgb = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return sum(a*b for a,b in zip(rgb,[.2126,.7152,.0722]))

for fg,bg,minimum in [('#176e69','#fdfefe',4.5),('#4d6262','#e3efed',4.5),('#87d0c6','#142222',4.5),('#b1c7c5','#263f3d',4.5),('#718686','#e3efed',3),('#789592','#263f3d',3)]:
    low,high = sorted([luminance(fg),luminance(bg)])
    ratio = (high+.05)/(low+.05)
    assert ratio >= minimum, (fg,bg,ratio)
    print(f'Contrast {fg} on {bg}: {ratio:.2f}:1 (minimum {minimum}) PASS')

print('PASS: README prose (except replaced banner), headings/sh/text blocks preserved; vision asset budget, local links, relative site assets, public path/copy scan, replay hashes/transcript binding, clean CLI check, GIF budget.')
