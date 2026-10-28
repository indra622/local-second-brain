"""Verify actual video encoding and the bounded presentation diff, without dependencies."""
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ffprobe = os.environ.get('FFPROBE', 'ffprobe')
ffmpeg = os.environ.get('FFMPEG', 'ffmpeg')
for lang in ('en', 'ko'):
    clip = ROOT / f'site/assets/report-scenario-v1-{lang}.mp4'
    probe = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames:format=duration,size', '-of', 'json', str(clip)]))
    stream = probe['streams'][0]
    assert stream == dict(codec_name='h264', width=1280, height=720, pix_fmt='yuv420p', r_frame_rate='24/1', nb_read_frames='816'), stream
    assert float(probe['format']['duration']) == 34
    assert int(probe['format']['size']) <= 6_000_000
    result = subprocess.run([ffmpeg, '-v', 'error', '-i', str(clip), '-f', 'null', '-'], capture_output=True, check=True)
    assert not result.stderr, result.stderr
    data = clip.read_bytes()
    assert data.index(b'moov') < data.index(b'mdat'), 'faststart'
    vtt = (ROOT / f'site/data/report-scenario-v1-{lang}.vtt').read_text()
    assert vtt.startswith('WEBVTT\n') and len(re.findall('-->', vtt)) == 6
    assert '00:00:34.000' in vtt
    assert (ROOT / f'site/assets/report-scenario-v1-{lang}.jpg').stat().st_size > 1000
    assert (ROOT / f'site/data/report-scenario-v1-{lang}.txt').stat().st_size > 1000
    print(lang, json.dumps(probe, ensure_ascii=False), 'full decode, faststart, captions, transcript, poster PASS')
for name in ('README.md', 'README.ko.md'):
    old = subprocess.check_output(['git', 'show', f'1870964:{name}'], cwd=ROOT, text=True)
    new = (ROOT / name).read_text()
    # The only README addition is one linked-poster paragraph and its explanatory links.
    stripped, count = re.subn(r'\[!\[[^\n]+report-scenario-v1-[^\n]+\n\n[^\n]+\n\n', '', new)
    assert count == 1 and stripped == old, name
    print(name, 'all prior prose, For agents, shell blocks, support/license and CLI evidence byte-identical PASS')
# Bound the tracked diff; no CLI, source data, evidence or global settings changes.
allowed = {'README.md', 'README.ko.md', 'site/app.js', 'site/index.html', 'site/styles.css'}
changed = subprocess.check_output(['git', 'diff', '--name-only', '1870964'], cwd=ROOT, text=True).splitlines()
assert all(p in allowed or p.startswith('scripts/outcome-video/') or re.match(r'site/(assets|data)/report-scenario-v1-', p) for p in changed), changed
print('Presentation-only diff and original evidence preserved PASS')
