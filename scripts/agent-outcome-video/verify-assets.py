"""Verify the agent report scenario assets and that the earlier clip files stay untouched. No dependencies."""
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ffprobe = os.environ.get('FFPROBE', 'ffprobe')
ffmpeg = os.environ.get('FFMPEG', 'ffmpeg')
PRIVATE = (b'/Users/', b'/Volumes/', b'/private/', b'/var/folders/', b'/home/')
for lang in ('ko', 'en'):
    clip = ROOT / f'site/assets/agent-report-v2-{lang}.mp4'
    probe = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames:format=duration,size', '-of', 'json', str(clip)]))
    stream = probe['streams'][0]
    assert stream == dict(codec_name='h264', width=1920, height=1080, pix_fmt='yuv420p', r_frame_rate='24/1', nb_read_frames='900'), stream
    assert float(probe['format']['duration']) == 37.5
    assert int(probe['format']['size']) <= 6_000_000
    result = subprocess.run([ffmpeg, '-v', 'error', '-i', str(clip), '-f', 'null', '-'], capture_output=True, check=True)
    assert not result.stderr, result.stderr
    data = clip.read_bytes()
    assert data.index(b'moov') < data.index(b'mdat'), 'faststart'
    vtt = ROOT / f'site/data/agent-report-v2-{lang}.vtt'
    text = vtt.read_text()
    assert text.startswith('WEBVTT\n') and len(re.findall('-->', text)) == 6 and '00:00:37.500' in text
    poster = ROOT / f'site/assets/agent-report-v2-{lang}.jpg'
    transcript = ROOT / f'site/data/agent-report-v2-{lang}.txt'
    assert poster.stat().st_size > 1000 and transcript.stat().st_size > 1000
    for generated in (clip, poster, vtt, transcript):
        blob = generated.read_bytes()
        assert not any(marker in blob for marker in PRIVATE), generated
    for public in (vtt, transcript):
        assert not re.search('[·—]', public.read_text()), public
    print(lang, json.dumps(probe, ensure_ascii=False), 'full decode, faststart, captions, transcript, poster, no private paths PASS')
# The earlier manual-handoff clip, its captions, transcripts and source stay byte-identical to the adoption base.
changed = subprocess.check_output(['git', 'diff', '--name-only', '5468457', '--'], cwd=ROOT, text=True).splitlines()
assert not any(re.match(r'(site/(assets|data)/report-scenario-v1-|scripts/outcome-video/|site/data/(sample|replay-|transcript))', p) for p in changed), changed
print('Earlier scenario assets, outcome-video source and sample data preserved PASS')
