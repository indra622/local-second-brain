'use strict';
let data = null, selected = null, tab = 'body', revision = null, historical = false;
const $ = id => document.getElementById(id);
const mobile = window.matchMedia('(max-width:850px)');
$('knowledge-nav').open = !mobile.matches;
mobile.addEventListener('change', () => { $('knowledge-nav').open = !mobile.matches; });
function el(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = String(text); if (cls) e.className = cls; return e; }
function add(parent, ...children) { parent.append(...children); return parent; }
function pre(text, cls) { return el('pre', typeof text === 'string' ? text : JSON.stringify(text, null, 2), cls); }
function button(text, action) { const b = el('button', text); b.type = 'button'; b.onclick = action; return b; }
function bad(n) { return !n || n.metadata_errors.length > 0; }
function lifecycle(n) { return bad(n) ? 'unknown' : ['draft', 'stable', 'deprecated'].includes(n.status) ? n.status : 'unknown'; }
function statusText(n) { return ({draft:'초안',stable:'안정 상태 선언',deprecated:'사용 중단 선언',unknown:'상태 확인 필요'})[lifecycle(n)]; }
function freshness(n) { return bad(n) || n.stale === null ? 'unknown' : n.stale ? 'stale' : 'fresh'; }
function freshText(n) { if(bad(n)) return '확인 기한 판정 불가'; return ({unknown:n?.stale_after ? '확인 기한 판정 불가' : '확인 기한 없음',stale:'확인 기한 지남',fresh:'확인 기한 전'})[freshness(n)]; }
function review(n) { if (bad(n)) return 'unknown'; const v = n.verified; return v && (!Array.isArray(v) || v.length) ? 'declared' : 'none'; }
function reviewText(n) { return ({unknown:'검토 선언 확인 불가',declared:'검토 선언 있음 (미인증)',none:'검토 선언 없음'})[review(n)]; }
function title(n, id) { return typeof n?.title === 'string' && n.title.trim() ? n.title : id; }
function open(path) { const n = data.notes[path]; if (!n) return; selected = n.id; revision = path; historical = path !== data.current[n.id]; tab = 'body'; renderList(); renderDetail(); $('detail').focus(); }
function renderList() {
  const query = $('query').value.trim().toLocaleLowerCase(); const list = $('notes'); list.replaceChildren(); let found = 0;
  for (const [id, path] of Object.entries(data.current)) {
    const n = data.notes[path];
    if (query && !(title(n,id) + '\n' + (n?.body || '')).toLocaleLowerCase().includes(query)) continue;
    if ($('status').value && $('status').value !== lifecycle(n)) continue;
    if ($('fresh').value && $('fresh').value !== freshness(n)) continue;
    if ($('review').value && $('review').value !== review(n)) continue;
    const b = button(title(n,id), () => { selected=id; revision=path; historical=false; renderList(); renderDetail();if(mobile.matches){$('knowledge-nav').open=false;$('detail').focus();$('detail').scrollIntoView();} });
    b.setAttribute('aria-pressed', String(selected === id));
    add(b,el('span', n ? `${statusText(n)} / ${freshText(n)}` : '현재 파일을 읽지 못했습니다', 'subtitle'));
    list.append(b); found++;
  }
  $('count').textContent = `${found} / ${Object.keys(data.current).length}개`;
  if (!found) list.append(el('p','이 화면에서 일치하는 노트가 없습니다. 원문과 과거 본문은 검색 범위에 포함되지 않습니다.','empty'));
}
function diffLines(before, after) {
  const a=before.split('\n'), b=after.split('\n');
  if(a.length*b.length>160000) return '큰 비교: 생략 없이 전체 이전/이후 텍스트를 표시합니다.\n--- 이전\n'+before+'\n+++ 이후\n'+after;
  const dp=Array.from({length:a.length+1},()=>new Uint16Array(b.length+1));
  for(let i=a.length-1;i>=0;i--) for(let j=b.length-1;j>=0;j--) dp[i][j]=a[i]===b[j]?dp[i+1][j+1]+1:Math.max(dp[i+1][j],dp[i][j+1]);
  let i=0,j=0,out=[]; while(i<a.length||j<b.length){if(i<a.length&&j<b.length&&a[i]===b[j]){out.push('  '+a[i]);i++;j++;}else if(j<b.length&&(i===a.length||dp[i][j+1]>=dp[i+1][j])) out.push('+ '+b[j++]);else out.push('- '+a[i++]);} return out.join('\n');
}
function historyPanel(n, container) {
  const paths=data.histories[n.id] || [];
  container.append(el('p','실제 저장된 리비전을 비교합니다. 본문이 같아도 검토 종류를 추정하지 않습니다.'));
  const row=el('div',undefined,'row'), left=el('select'),right=el('select');left.setAttribute('aria-label','이전 리비전');right.setAttribute('aria-label','이후 리비전');
  for(const path of paths) for(const select of [left,right]) { const o=el('option', path.split('/').pop()+(path===data.current[n.id]?' (현재 선택)':''));o.value=path;select.append(o); }
  left.value=paths[Math.max(0,paths.length-2)];right.value=revision;
  add(row,add(el('label','이전 기록'),left),add(el('label','이후 기록'),right));container.append(row);
  const result=el('div');container.append(result);
  function compare(){result.replaceChildren();const a=data.notes[left.value],b=data.notes[right.value];if(!a||!b){result.append(el('p','선택한 리비전을 읽지 못했습니다.','warning'));return;}
    let label=bad(a)||bad(b)?'형식 오류가 있어 변경 종류를 판정할 수 없습니다.':a.body!==b.body?'본문이 달라졌습니다.':a.sha256===b.sha256?'동일한 파일입니다.':'본문은 같고 메타데이터 또는 직렬화만 달라졌습니다. 검토 종류는 아래 선언을 직접 확인하세요.';
    result.append(el('p',label,'notice'));
    const pair=el('div',undefined,'compare');for(const x of [a,b]) {const col=el('div');add(col,button(x.path.split('/').pop()+' 기록 열기',()=>open(x.path)),pre(x.body,'reading'));pair.append(col);}result.append(pair);
    result.append(el('h3','본문 차이'),pre(diffLines(a.body,b.body)));
    const details=el('details');add(details,el('summary','메타데이터 차이'),pre(diffLines(JSON.stringify(a.metadata,null,2),JSON.stringify(b.metadata,null,2))));result.append(details);
  }left.onchange=compare;right.onchange=compare;compare();
}
function sourcesPanel(n, container) {
  container.append(el('h3','생각의 근거가 된 원문'));
  if(!n.source_ids.length) container.append(el('p','지원하는 경로로 연결된 원문이 없습니다. 연결 선언을 확인해 주세요. 원문 자체가 없다는 뜻은 아닙니다.','warning'));
  for(const id of n.source_ids){const s=data.sources[id],d=el('details');d.open=true;
    const name=typeof s.provenance?.original_name==='string'?s.provenance.original_name:id;
    d.append(el('summary',name));
    const state=s.state==='available'?'보존 원문을 읽었습니다.':s.state==='non-utf8'?'텍스트로 표시할 수 없는 형식입니다.':'보존 원문을 읽지 못했습니다.';
    const match=s.hash_matches_declaration===true?'보존 바이트가 출처의 해시 선언과 일치합니다.':s.hash_matches_declaration===false?'출처의 해시 선언과 다릅니다.':'해시 선언을 확인할 수 없습니다.';
    d.append(el('p',state+' '+match,'path'));
    d.append(pre(s.text === null ? '표시할 수 있는 원문 텍스트가 없습니다.' : s.text,'reading'));
    const meta=el('details');add(meta,el('summary','출처 기록과 바이트 식별 정보'),pre({sha256:s.sha256,bytes:s.bytes,provenance:s.provenance}));d.append(meta);
    if(s.error||s.provenance_error||s.hash_matches_declaration===false)d.append(el('p',s.error||s.provenance_error||'보존 원문과 출처 선언을 확인해 주세요.','warning'));container.append(d);}
  const context=n.metadata['x-second-brain-annotations'];
  const declared=el('details');add(declared,el('summary','정리의 작성 선언과 별도 맥락 확인'),pre({generated:n.generated,context:context?.context || '별도로 구조화된 맥락 선언 없음'}));container.append(declared);
  const refs=el('details');add(refs,el('summary','출처 연결 선언과 지원 상태'),pre(n.source_refs));container.append(refs);
}
function relatedPanel(n, container) {
  container.append(el('p','노트에 남긴 연결과 그 근거를 따라갑니다. 지원하지 않는 경로나 외부 주소는 열지 않습니다.','path'));
  if(n.related_partial)container.append(el('p','연결 표시 한도에 도달했습니다. 전체 관계 수는 알 수 없습니다.','warning'));
  if(!n.related.length)container.append(el('p','지원하는 파서 범위에서 표시할 연결을 찾지 못했습니다. 전체적인 관련 없음 판정은 아닙니다.'));
  for(const link of n.related){const row=el('div',undefined,'link-item');
    const kind=({'relates_to':'관련 기록','depends_on':'의존하는 기록','supersedes':'대체하는 기록','contradicts':'상충한다고 선언한 기록','supports':'뒷받침하는 기록'})[link.kind]||link.kind;
    row.append(el('strong',kind));
    const state=({'available':'이 화면에서 읽은 기록입니다.','unchecked':'이 화면에서 확인하지 않은 참조입니다.','unsafe':'안전한 읽기 범위로 확인할 수 없는 경로입니다.','unavailable-or-out-of-scope':'읽기 범위 밖이거나 확인하지 못한 기록입니다.'})[link.state]||'연결 상태를 확인할 수 없습니다.';
    row.append(el('p',state+(link.line?' 근거는 본문 '+link.line+'행의 링크입니다.':'')));
    if(link.path&&data.notes[link.path])row.append(button(title(data.notes[link.path],link.path)+' 열기',()=>open(link.path)));
    const detail=el('details');add(detail,el('summary','연결 선언과 근거 보기'),pre({resource:link.resource,path:link.path,evidence:link.evidence||'별도 관계 근거 선언 없음'}));row.append(detail);container.append(row);}

}
function renderDetail(){const container=$('detail');container.replaceChildren();if(!selected){container.append(el('p','현재 선택된 노트가 없습니다.','empty'));return;}const path=revision||data.current[selected],n=data.notes[path];
  if(!n){container.append(el('h2',selected),el('p','현재 선택 경로를 읽지 못했습니다. 누락 또는 갱신 중 변경일 수 있습니다.','warning'),el('p',path,'path'));return;}
  add(container,el('p',n.current?'현재 선택된 기록':'이전 기록 / 현재 선택 아님','eyebrow'),el('h2',title(n,n.id)),el('p',n.path.split('/').pop().replace('.md','')+' 기록','path'));
  const badges=el('div',undefined,'badges');for(const text of [statusText(n),freshText(n),reviewText(n)])badges.append(el('span',text,'badge'));container.append(badges);
  if(n.metadata_errors.length)container.append(el('p','확인 필요: '+n.metadata_errors.join(' / '),'warning'));
  if(n.stale_after)container.append(el('p','선언된 확인 기한: '+String(n.stale_after),'path'));
  const tabs=el('nav',undefined,'tabs');tabs.setAttribute('aria-label','노트 보기');for(const [key,label] of [['body','정리 본문'],['history','이전 기록과 차이'],['sources','원문과 맥락'],['related','연결 탐색']]){const b=button(label,()=>{tab=key;renderDetail();const active=container.querySelector('[aria-pressed="true"]');active?.focus();});b.setAttribute('aria-pressed',String(tab===key));tabs.append(b);}container.append(tabs);
  const panel=el('section');container.append(panel);
  if(tab==='body'){panel.append(pre(n.body,'reading'));const d=el('details');add(d,el('summary','기록 위치와 메타데이터 / 검토 선언'),pre({path:n.path,...n.metadata}));panel.append(d);}
  if(tab==='history')historyPanel(n,panel);if(tab==='sources')sourcesPanel(n,panel);if(tab==='related')relatedPanel(n,panel);
}
async function refresh(){const b=$('refresh');b.disabled=true;b.textContent='읽는 중…';try{const response=await fetch('./api/snapshot',{cache:'no-store',signal:AbortSignal.timeout(20000)});const next=await response.json();if(!response.ok)throw new Error(next.error||'갱신 실패');if(!next.current||!next.notes)throw new Error('응답 형식을 확인할 수 없습니다.');data=next;if(!selected||!(selected in data.current)){selected=Object.keys(data.current)[0]||null;revision=selected?data.current[selected]:null;}else if(!historical || !data.notes[revision]){revision=data.current[selected];historical=false;}
  $('error').hidden=true;$('scan').textContent='마지막 성공: '+new Date(data.completed_at).toLocaleString('ko-KR');$('coverage').textContent=`${data.bundle} / ${Object.keys(data.current).length}개의 지식${data.partial?' / 일부 기록을 읽지 못했습니다.':''}`;
  $('scan-technical').textContent=`스캔 시작 ${new Date(data.scanned_at).toLocaleString('ko-KR')} / ${data.partial?'미확인 파일 '+data.diagnostics.length+'건':'읽은 파일 바이트 재확인 완료'}. 동시 변경의 원자적 스냅샷은 아닙니다. 누락 기록: ${JSON.stringify(data.diagnostics)}`;renderList();renderDetail();
  }catch(error){$('error').textContent='새로 읽지 못했습니다. '+error.message+(data?' 마지막 성공 화면을 유지합니다.':' 아직 성공한 화면이 없습니다.');$('error').hidden=false;}finally{b.disabled=false;b.textContent='새로 읽기';}}
for(const id of ['query','status','fresh','review'])$(id).addEventListener(id==='query'?'input':'change',()=>{if(data)renderList();});$('refresh').onclick=refresh;refresh();
