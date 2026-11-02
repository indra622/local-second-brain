"""Render the compact README canvas from the pinned Archify semantic sources.

Run with Python 3.11+: python docs/assets/architecture/v1/render.py
PNG rendering is documented in README.md; no runtime or third-party imports.
"""
from pathlib import Path
import json
from html import escape

HERE = Path(__file__).resolve().parent
BOXES = {'person': (30, 70), 'agent': (340, 70), 'cli': (650, 70),
         'kit': (30, 370), 'viewer': (340, 370), 'bundle': (650, 370)}
ROUTES = {
    'ask': ('M250 103 H340', 295, 91),
    'answer': ('M340 149 H250', 295, 174),
    'instruct': ('M140 370 V280 H450 V180', 295, 269),
    'invoke': ('M560 103 H650', 605, 91),
    'result': ('M650 149 H560', 605, 174),
    'persist': ('M800 180 V370', 851, 303),
    'read-files': ('M505 180 V225 H710 V370', 627, 214),
    'open': ('M560 425 H650', 605, 413),
}
COPY = {
    'ko': {
        'person': ['사용자', '목표와 접근 범위 결정'],
        'agent': ['외부 AI 에이전트', '의미 정리 / 연결 / 답변'],
        'cli': ['second-brain CLI', '저장 / 검색 / 이력 / 진단', 'Python + PyYAML'],
        'kit': ['지식 키트 + 프로필', '번들 밖의 문서와 설정', '에이전트가 읽고 적용'],
        'viewer': ['선택적 뷰어', 'Markdown / Obsidian', '별도 GUI 제공 없음'],
        'bundle': ['로컬 지식 폴더', '원문 / 노트 리비전', '현재 index + 사람용 탐색'],
        'edges': ['목표', '답변', '명시적 활성화', '명령', '결과', '읽기 / 보존', '허가 범위의 직접 읽기', '열람'],
        'footer': '실선: 명령과 의존 관계   |   점선: CLI를 거치지 않는 읽기',
    },
    'en': {
        'person': ['User', 'Sets goals and access'],
        'agent': ['External AI agent', 'Curate / connect / answer'],
        'cli': ['second-brain CLI', 'Store / query / diagnose', 'Python + PyYAML'],
        'kit': ['Kit + profile', 'Docs outside the bundle', 'Read and applied by agent'],
        'viewer': ['Optional viewer', 'Markdown / Obsidian', 'No shipped GUI'],
        'bundle': ['Knowledge bundle', 'Originals / note revisions', 'Current index + human nav'],
        'edges': ['Goals', 'Answer', 'Activate explicitly', 'Run', 'Result', 'Read / store', 'Authorized direct read', 'Open'],
        'footer': 'Solid: commands and dependencies   |   Dashed: reading without the CLI',
    },
}

def render(locale):
    source = json.loads((HERE / f'approved.{locale}.json').read_text())
    text = COPY[locale]
    assert set(BOXES) == {c['id'] for c in source['components']}
    assert list(ROUTES) == [c['id'] for c in source['connections']]
    svg = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" width="930" height="540" viewBox="0 0 930 540" role="img" aria-labelledby="title desc" xml:lang="{locale}">',
           f'<title id="title">{escape(source["meta"]["title"])}</title>',
           '<desc id="desc">' + escape(' / '.join(c['label'] for c in source['connections'])) + '</desc>',
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="#475569"/></marker></defs>',
           '<rect width="930" height="540" rx="14" fill="#ffffff"/>',
           '<g font-family="Arial, Apple SD Gothic Neo, Noto Sans KR, sans-serif" fill="#172b4d">']
    colors = {'person': '#f1f5f9', 'agent': '#edf2ff', 'cli': '#edf2ff',
              'kit': '#f7f0ff', 'viewer': '#eaf8f5', 'bundle': '#fff6e5'}
    for component in source['components']:
        ident = component['id']; x, y = BOXES[ident]
        svg.append(f'<g id="{ident}"><rect x="{x}" y="{y}" width="220" height="110" rx="12" fill="{colors[ident]}" stroke="#94a3b8"/>')
        for n, line in enumerate(text[ident]):
            size = 20 if n == 0 else 16
            weight = '600' if n == 0 else '400'
            svg.append(f'<text x="{x+110}" y="{y+33+n*26}" text-anchor="middle" font-size="{size}" font-weight="{weight}">{escape(line)}</text>')
        svg.append('</g>')
    for connection, label in zip(source['connections'], text['edges']):
        ident = connection['id']; path, x, y = ROUTES[ident]
        dash = ' stroke-dasharray="7 6"' if connection.get('variant') == 'dashed' else ''
        svg.append(f'<g id="{ident}" data-from="{connection["from"]}" data-to="{connection["to"]}"><path d="{path}" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"{dash}/><text x="{x}" y="{y}" text-anchor="middle" font-size="17" stroke="#ffffff" stroke-width="5" paint-order="stroke" stroke-linejoin="round">{escape(label)}</text></g>')
    svg.append(f'<text x="465" y="520" text-anchor="middle" font-size="16">{escape(text["footer"])}</text></g></svg>')
    (HERE / f'local-second-brain.{locale}.svg').write_text('\n'.join(svg)+'\n')

if __name__ == '__main__':
    for language in COPY:
        render(language)
