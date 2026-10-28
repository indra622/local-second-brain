'use strict';
const ko = new URLSearchParams(location.search).get('lang') === 'ko';
const copy = {
  skip:'예제 탐색으로 건너뛰기',theme:'테마 바꾸기',hero:'AI와 쌓은 지식, 대화 밖에서도 이어서.',sub:'원문과 함께 남기고, 다음 작업에 다시 쓰는 나만의 지식 저장소.',explore:'예제 살펴보기',install:'설치하기',mark:'내 노트와 원문을 다음 작업에도.',benefit:'한 번 정리한 지식을 다시 쓰세요',example:'보고서 제출일이 금요일에서 목요일로 바뀌었습니다. 노트를 열고 원문과 이전 버전을 비교해 보세요.',disclosure:'CLI가 저장한 파일을 설명하는 브라우저 예제입니다. 제품에 포함된 GUI나 실시간 에이전트 대화가 아닙니다. 모든 예제 글은 미리 준비한 가상 자료이며 모델이 생성하지 않았습니다.',filter:'예제 노트 필터',filterHelp:'제목과 모든 버전의 본문에서 부분 문자열을 찾는 브라우저 필터입니다. CLI 검색은 정확한 단어를 찾습니다.',noResults:'일치하는 노트가 없습니다. 검색어를 지우거나 예제를 초기화하세요.',reset:'예제 초기화',savedNote:'저장한 노트',revision:'버전',compare:'변경 내용 비교',sources:'저장한 원문 확인',next:'다음 작업에서 에이전트에게 건넬 것',handoff:'현재 노트와 원문을 함께 전달하세요. 저장한 규칙에 맞춰 새 보고서를 쓰고, 확인이 필요한 내용은 표시해 달라고 요청하세요.',trust:'예제 노트는 초안(draft)이며 검토 기록이 없어 unverified로 표시됩니다. fresh는 예제 기준일인 2026년 10월 28일에 재확인 기한이 지나지 않았다는 뜻일 뿐입니다. 2030년 1월 1일부터는 stale로 표시됩니다. 사실 검증을 뜻하지 않습니다.',sampleLanguage:'언어를 바꿔도 원문 파일과 CLI 출력은 원래 언어인 영어로 표시합니다.',evidence:'결론의 근거까지 함께 남기세요',replayIntro:'실제 CLI가 노트를 저장하고, 다시 찾고, 바뀐 규칙을 비교하는 과정을 보세요.',play:'CLI 재생 보기',stop:'정지하고 포스터 보기',caption:'실제 CLI 출력 중 일부입니다. 재생 시간을 조정하고 임시 경로를 바꿨습니다. 전체 출력은 아래에서 볼 수 있습니다. 미리 준비한 가상 자료이며 모델 호출은 없습니다.',poster:'정지 이미지 열기',transcript:'CLI 출력 읽기',download:'텍스트 출력 열기',files:'AI를 바꿔도 파일은 내게 남습니다',filesBody:'노트는 Markdown으로, 원문은 수집 당시의 바이트 그대로 남습니다. 다음 에이전트에게 전달할 파일을 직접 고르세요.',limits:'현재 제품은 초기 알파 CLI입니다. 자료를 고르고 작성과 재사용을 지시하는 일은 사용자가 맡습니다. 자동 기억, 모델 연동, 의미 검색은 없습니다.',data:'공개 예제 데이터 확인',error:'예제를 불러오지 못했습니다. 로컬 HTTP 서버로 열거나 공개 예제 데이터를 확인해 주세요.',current:'현재',older:'이전',source:'원문',only:'이 노트는 저장한 버전이 하나입니다.',diff:'실제 CLI diff 출력',empty:'비교할 변경 내용이 없습니다.'
};
const en = {stop:'Stop and show poster',current:'current',older:'earlier',source:'Source',only:'This note has one saved revision.',diff:'Actual CLI diff output',empty:'No changes to compare.',error:'Could not load the sample. Use a local HTTP server or inspect the public sample data.'};
const t = key => (ko ? copy[key] : en[key]);
if (ko) {
  document.documentElement.lang = 'ko';
  document.title = 'Local Second Brain | 대화 밖에서도 이어지는 지식';
  document.querySelector('meta[name=description]').content = '원문과 함께 노트를 저장하고 다음 AI 작업에 다시 쓰세요. Local Second Brain 파일과 버전을 예제로 살펴보세요.';
  document.querySelectorAll('[data-t]').forEach(el => { if(copy[el.dataset.t]) el.textContent = copy[el.dataset.t]; });
  const locale = document.querySelector('#locale');
  locale.href = '?lang=en'; locale.lang = 'en'; locale.textContent = 'English';
  document.querySelector('#install-link').href = 'https://github.com/indra622/local-second-brain/blob/main/README.ko.md#시작하기';
  document.querySelector('nav').setAttribute('aria-label','환경 설정');
  document.querySelector('#notes').setAttribute('aria-label','예제 노트');
  document.querySelector('.brand-figure img').alt = '폴더와 문서가 연결된 로고';
  document.querySelector('#replay-image').alt = '실제 CLI 출력: 보고서 규칙 저장과 검색, 금요일에서 목요일로 바뀐 내용 비교.';
}
document.querySelector('#theme').addEventListener('click', () => {
  const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.theme = dark ? 'light' : 'dark';
});
const $ = id => document.getElementById(id);
let data, selected = 0, revision = 0, compare = false, playing = false;
function currentIndex(note) { return note.revisions.findIndex(item => item.current === true); }
function renderNote() {
  const note = data.notes[selected], rev = note.revisions[revision];
  $('note-title').textContent = ko ? note.titleKo : rev.title;
  $('revision').replaceChildren(...note.revisions.map((item, i) => {
    const option = document.createElement('option'); option.value = i;
    option.textContent = `v${i+1} (${item.current ? t('current') : t('older')})`;
    option.selected = i === revision; return option;
  }));
  $('compare').disabled = note.revisions.length < 2;
  $('compare').setAttribute('aria-pressed', String(compare));
  $('status').textContent = `${rev.current ? t('current') : t('older')} | ${rev.status} | ${rev.trust} | ${rev.stale ? 'stale' : 'fresh'} (2026-10-28)`;
  $('file-path').textContent = compare ? t('diff') : rev.path;
  $('body').textContent = compare ? (note.diff || t('empty')) : rev.body;
  $('sources').replaceChildren(...rev.metadata.sources.map(source => {
    const div = document.createElement('div'); div.className = 'source';
    const title = document.createElement('p'); title.textContent = `${t('source')}: ${source.id}`;
    const pre = document.createElement('pre'); pre.textContent = note.sources[source.id].text;
    const hash = document.createElement('code'); hash.textContent = `SHA-256: ${note.sources[source.id].sha256}`;
    div.append(title,pre,hash); return div;
  }));
  $('handoff-path').textContent = note.revisions[currentIndex(note)].path;
}
function renderList() {
  const query = $('search').value.trim().toLocaleLowerCase();
  let found = 0;
  $('notes').replaceChildren(...data.notes.flatMap((note,i) => {
    const text = [note.titleKo,...note.revisions.map(r => `${r.title} ${r.body}`)].join(' ').toLocaleLowerCase();
    if (!text.includes(query)) return [];
    found++;
    const button = document.createElement('button'); button.textContent = ko ? note.titleKo : note.revisions[0].title;
    button.setAttribute('aria-pressed',String(i === selected));
    button.addEventListener('click', () => {selected=i; revision=currentIndex(note); compare=false; $('source-details').open=false; renderNote(); renderList(); $('notes').querySelector('[aria-pressed="true"]')?.focus();});
    return [button];
  }));
  $('no-results').hidden = found > 0;
  $('note-panel').hidden = found === 0;
}
$('search').addEventListener('input', renderList);
$('revision').addEventListener('change', () => {revision=Number($('revision').value);compare=false;renderNote();});
$('compare').addEventListener('click', () => {compare=!compare;renderNote();});
$('reset').addEventListener('click', () => {selected=0;revision=currentIndex(data.notes[0]);compare=false;$('search').value='';$('source-details').open=false;renderList();renderNote();});
$('play').addEventListener('click', () => {
  playing=!playing;
  $('replay-image').src = playing ? 'assets/cli-demo.gif' : 'assets/cli-poster.png';
  $('play').textContent = playing ? t('stop') : (ko ? copy.play : 'Play CLI replay');
  $('play').setAttribute('aria-pressed',String(playing));
});
Promise.all([fetch('data/sample.json').then(r => {if(!r.ok) throw Error(r.status);return r.json();}),fetch('data/transcript.txt').then(r => {if(!r.ok) throw Error(r.status);return r.text();})]).then(([sample, transcript]) => {
  if(!sample.notes?.length || sample.notes.some(n => currentIndex(n) < 0)) throw Error('Invalid sample');
  data=sample;revision=currentIndex(data.notes[0]);renderList();renderNote();$('transcript').textContent=transcript;$('load-state').hidden=true;$('workbench').hidden=false;
}).catch(() => {$('load-state').textContent=t('error');});
