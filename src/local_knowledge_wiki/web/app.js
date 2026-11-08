'use strict';
let data = null, selected = null, tab = 'body', revision = null, historical = false, view = 'home', drillSpec = null, topicFilter = '', mapSelected = null, mapFocus = null, mapHops = 0;
let handoffPending = true;
let mapViewport = {x:0,y:0,w:1000,h:600};
let layoutCache = {key:null,positions:null};
const $ = id => document.getElementById(id);
const owns = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const mobile = window.matchMedia('(max-width:850px)');
$('knowledge-nav').open = !mobile.matches;
mobile.addEventListener('change', () => { $('knowledge-nav').open = !mobile.matches;if(data)renderHome(); });
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
function open(path) {
  const n=data.notes[path];
  if(n) drill({kind:'record',id:n.id},'선택한 기록','body',path);
}
function readHandoff(hash,snapshot) {
  if(typeof hash!=='string'||!hash.includes('note='))return null;
  const fail={error:'요청한 기록을 현재 읽기 범위에서 확인하지 못했습니다. 현재 목록을 표시합니다.'};
  if(hash.length>512)return fail;
  const values=new URLSearchParams(hash.slice(1));
  if([...values].length!==3||['note','revision','panel'].some(key=>values.getAll(key).length!==1))return fail;
  const id=values.get('note'),rev=values.get('revision'),panel=values.get('panel');
  if(!/^[a-z0-9][a-z0-9-]{0,63}$/.test(id)||!/^r[0-9]{6}$/.test(rev)||rev==='r000000'||!['body','sources','history','related'].includes(panel)||!owns(snapshot.current,id))return fail;
  const path=`concepts/${id}/${rev}.md`;
  if(!owns(snapshot.notes,path)||snapshot.notes[path].id!==id)return fail;
  return {id,path,panel};
}
function applyHandoff() {
  if(!handoffPending)return;
  handoffPending=false;
  const target=readHandoff(window.location?.hash||'',data);
  if(!target)return;
  if(target.error){$('handoff-notice').textContent=target.error;$('handoff-notice').hidden=false;return;}
  selected=target.id;mapSelected=target.id;revision=target.path;historical=revision!==data.current[selected];
  drillSpec={kind:'record',id:selected};tab=target.panel;view='explore';
  $('drill-banner').hidden=false;$('drill-label').textContent='Astryx에서 선택한 정확한 기록';
}
function categoryIds(spec, model) {
  if (!spec) return null;
  if (spec.kind === 'record') return [spec.id];
  if (spec.kind === 'group') return model.groups[spec.family][spec.key];
  if (spec.kind === 'source') return [...new Set(model.sourceGroups[spec.key].flatMap(sid=>model.sourceOwners[sid] || []))];
  return model[spec.kind];
}
function baseMatchingIds() {
  if(!data)return [];
  const members=categoryIds(drillSpec,homeModel(data));
  const query=$('query').value.trim().toLocaleLowerCase();
  return Object.entries(data.current).filter(([id,path])=>{
    const n=data.notes[path];
    return (!members || members.includes(id))
      && (!query || (title(n,id)+'\n'+(n?.body||'')).toLocaleLowerCase().includes(query))
      && (!$('status').value || $('status').value===lifecycle(n))
      && (!$('fresh').value || $('fresh').value===freshness(n))
      && (!$('review').value || $('review').value===review(n))
      && (!topicFilter || JSON.stringify(KnowledgeMap.topic(n))===topicFilter);
  }).map(([id])=>id);
}
function matchingIds() {
  const ids=baseMatchingIds();
  if(!mapHops || !mapFocus)return ids;
  const scope=KnowledgeMap.neighborhood(KnowledgeMap.model(data),mapFocus,mapHops,new Set(ids));
  return ids.filter(id=>scope.has(id));
}
function reconcileSelection() {
  if(mapFocus && !baseMatchingIds().includes(mapFocus)){mapFocus=null;mapHops=0;}
  const ids=matchingIds();
  if(!selected || !owns(data.current,selected) || !ids.includes(selected)) {
    selected=ids[0]||null;revision=selected?data.current[selected]:null;historical=false;
  } else if(!historical || !owns(data.notes,revision)) {
    revision=data.current[selected];historical=false;
  }
}
function renderList() {
  const list=$('notes');list.replaceChildren();const ids=matchingIds();
  for (const id of ids) {
    const path=data.current[id],n=data.notes[path];
    const b = button(title(n,id), () => { selected=id; revision=path; historical=false; renderList(); renderDetail();if(mobile.matches){$('knowledge-nav').open=false;$('detail').focus();$('detail').scrollIntoView();} });
    b.setAttribute('aria-pressed', String(selected === id));
    add(b,el('span', n ? `${statusText(n)} / ${freshText(n)}` : '현재 파일을 읽지 못했습니다', 'subtitle'));
    list.append(b);
  }
  $('count').textContent = `${ids.length} / ${Object.keys(data.current).length}개`;
  if (!ids.length) list.append(el('p','이 화면에서 일치하는 노트가 없습니다. 원문과 과거 본문은 검색 범위에 포함되지 않습니다.','empty'));
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
async function refresh(){const b=$('refresh');b.disabled=true;b.textContent='읽는 중…';try{const response=await fetch('./api/snapshot',{cache:'no-store',signal:AbortSignal.timeout(20000)});const next=await response.json();if(!response.ok)throw new Error(next.error||'갱신 실패');if(!next.current||!next.notes)throw new Error('응답 형식을 확인할 수 없습니다.');data=next;applyHandoff();reconcileSelection();
  $('error').hidden=true;$('scan').textContent='마지막 성공: '+new Date(data.completed_at).toLocaleString('ko-KR');$('coverage').textContent=`${data.bundle} / ${Object.keys(data.current).length}개의 지식${data.partial?' / 일부 기록을 읽지 못했습니다.':''}`;
  $('scan-technical').textContent=`스캔 시작 ${new Date(data.scanned_at).toLocaleString('ko-KR')} / ${data.partial?'미확인 파일 '+data.diagnostics.length+'건':'읽은 파일 바이트 재확인 완료'}. 동시 변경의 원자적 스냅샷은 아닙니다. 누락 기록: ${JSON.stringify(data.diagnostics)}`;renderList();renderDetail();renderHome();showView(view);
  }catch(error){$('error').textContent='새로 읽지 못했습니다. '+error.message+(data?' 마지막 성공 화면을 유지합니다.':' 아직 성공한 화면이 없습니다.');$('error').hidden=false;}finally{b.disabled=false;b.textContent='새로 읽기';}}
for(const id of ['query','status','fresh','review'])$(id).addEventListener(id==='query'?'input':'change',()=>{if(data){reconcileSelection();renderList();renderDetail();renderHome();}});$('refresh').onclick=refresh;
$('topic').onchange=()=>{topicFilter=$('topic').value;reconcileSelection();renderList();renderDetail();renderHome();};
$('nav-home').onclick=()=>{if(selected && matchingIds().includes(selected))mapSelected=selected;renderHome();showView('home');};
$('nav-explore').onclick=()=>showView('explore');
$('clear-drill').onclick=()=>drill(null,'전체 지식');
refresh();

function deadline(n) {
  if (!n) return 'missing';
  if (bad(n)) return 'invalid';
  if (n.stale === true) return 'overdue';
  if (n.stale === false) return 'before';
  return n.stale_after ? 'unknown' : 'none';
}
function homeModel(snapshot) {
  const entries = Object.entries(snapshot.current);
  const groups = {deadline:{overdue:[],before:[],none:[],unknown:[],invalid:[],missing:[]}, review:{declared:[],none:[],unknown:[]}, status:{draft:[],stable:[],deprecated:[],unknown:[]}};
  const sourceIds = new Set(), sourceOwners = Object.create(null), attention = [], unsupported = [], unlinked = [];
  let currentRead = 0;
  for (const [id,path] of entries) {
    const n = snapshot.notes[path];
    groups.deadline[deadline(n)].push(id);
    groups.review[review(n)].push(id);
    groups.status[lifecycle(n)].push(id);
    if (!n) { attention.push(id); continue; }
    currentRead++;
    let needsAttention = bad(n) || deadline(n) === 'overdue';
    if ((n.source_refs || []).some(ref=>ref.state !== 'canonical-binding')) { unsupported.push(id); needsAttention=true; }
    if (!(n.source_refs || []).length) unlinked.push(id);
    for (const sid of n.source_ids) {
      sourceIds.add(sid); (sourceOwners[sid] ||= []).push(id);
      const s = owns(snapshot.sources,sid)?snapshot.sources[sid]:null;
      if (!s || s.state !== 'available' || s.provenance_error || s.hash_matches_declaration !== true) needsAttention=true;
    }
    if (needsAttention) attention.push(id);
  }
  const sourceGroups = {available:[],nontext:[],unavailable:[],provenance:[]};
  for (const sid of sourceIds) {
    const s=owns(snapshot.sources,sid)?snapshot.sources[sid]:null;
    sourceGroups[s?.state==='available'?'available':s?.state==='non-utf8'?'nontext':'unavailable'].push(sid);
    if (!s || s.provenance_error || s.hash_matches_declaration !== true) sourceGroups.provenance.push(sid);
  }
  let unknownTime=0;
  const recent=Object.values(snapshot.notes).map(n=>{
    const at=n.generated?.at;
    const time=!bad(n) && typeof at==='string' && /^\d{4}-\d\d-\d\d[Tt]\d\d:\d\d:\d\d(?:\.\d+)?(?:[Zz]|[+-]\d\d:\d\d)$/.test(at)?Date.parse(at):NaN;
    if(!Number.isFinite(time)) unknownTime++;
    return {note:n,time};
  }).filter(x=>Number.isFinite(x.time)).sort((a,b)=>b.time-a.time || a.note.path.localeCompare(b.note.path));
  return {groups,sourceGroups,sourceOwners,sourceCount:sourceIds.size,unsupported,unlinked,attention,currentCount:entries.length,currentRead,revisions:Object.keys(snapshot.notes).length,recent,unknownTime};
}
function showView(next) {
  view=next;
  $('home').hidden=view!=='home';$('explore').hidden=view!=='explore';
  $('nav-home').setAttribute('aria-pressed',String(view==='home'));
  $('nav-explore').setAttribute('aria-pressed',String(view==='explore'));
  $('screen-title').textContent=view==='home'?'지식 현황':'지식 탐색';
}
function drill(spec,label,targetTab='body',path=null) {
  if(!data) return;
  drillSpec=spec;
  if(spec?.kind==='record')mapSelected=spec.id;
  for(const id of ['query','status','fresh','review'])$(id).value='';
  topicFilter='';mapHops=0;mapFocus=null;
  $('drill-banner').hidden=drillSpec===null;
  $('drill-label').textContent=label;
  selected=spec?.kind==='record'?spec.id:null;revision=path;
  historical=!!revision && revision!==data.current[selected];tab=targetTab;
  reconcileSelection();
  showView('explore');renderList();renderDetail();renderHome();
  if(mobile.matches)$('knowledge-nav').open=false;
  $('screen-title').scrollIntoView();$('detail').focus({preventScroll:true});
}
function panel(titleText, subtitle) {
  const box=el('section',undefined,'home-panel');box.append(el('h2',titleText));
  if(subtitle)box.append(el('p',subtitle,'panel-subtitle'));
  return box;
}
function distribution(titleText, subtitle, items, total, family) {
  const box=panel(titleText,subtitle);
  for(const [label,ids,tone,key] of items) {
    const b=button('',()=>drill({kind:'group',family,key},label));b.className='distribution-row';
    add(b,el('span',label),el('strong',ids.length));
    const track=el('span',undefined,'bar-track'),bar=el('span',undefined,'bar '+tone);
    bar.style.width=(total?100*ids.length/total:0)+'%';track.append(bar);b.append(track);box.append(b);
  }
  if(!total)box.append(el('p','표시할 현재 선택이 없습니다.','path'));
  return box;
}
function renderHome() {
  if(!data)return;
  const model=homeModel(data),home=$('home');home.replaceChildren();
  const cards=el('div',undefined,'stat-grid');
  function stat(key,label,value,description,spec,targetTab='body',tone='') {
    const b=button('',()=>drill(spec,label,targetTab));b.className='stat-card '+tone;b.dataset.stat=key;
    add(b,el('span',label,'stat-label'),el('strong',value,'stat-value'),el('span',description,'stat-description'));cards.append(b);
  }
  stat('current','현재 지식',model.currentCount,model.currentRead+'개 본문 확인 / '+(model.currentCount-model.currentRead)+'개 파일 미확인',null);
  stat('revisions','읽은 리비전',model.revisions,'현재 주제의 과거 기록 포함'+(data.partial?' / 일부 미확인':''),null,'history');
  stat('overdue','확인 기한 지남',model.groups.deadline.overdue.length,'현재 기록 중 판정 가능한 기한 기준',{kind:'group',family:'deadline',key:'overdue'},'body','amber');
  stat('attention','확인이 필요한 기록',model.attention.length,'기한 초과, 형식 또는 출처 확인 필요',{kind:'attention'},'sources','amber');
  home.append(cards);
  renderMapHome(home);
  const grid=el('div',undefined,'panel-grid');
  grid.append(distribution('확인 기한','현재 지식 기준 / 미지정과 판정 불가를 구분합니다.',[
    ['기한 지남',model.groups.deadline.overdue,'amber','overdue'],['기한 전',model.groups.deadline.before,'teal','before'],['기한 미지정',model.groups.deadline.none,'muted','none'],['기한 판정 불가',model.groups.deadline.unknown,'muted','unknown'],['형식 확인 필요',model.groups.deadline.invalid,'amber','invalid'],['현재 파일 미확인',model.groups.deadline.missing,'red','missing']],model.currentCount,'deadline'));
  grid.append(distribution('검토 선언','사람 인증이나 내용의 사실 확인 수가 아닙니다.',[
    ['선언 있음',model.groups.review.declared,'teal','declared'],['선언 없음',model.groups.review.none,'muted','none'],['선언 확인 불가',model.groups.review.unknown,'amber','unknown']],model.currentCount,'review'));
  grid.append(distribution('기록 상태','현재 선택에 기록된 상태 / 생략 시 기존 기본값을 따릅니다.',[
    ['초안',model.groups.status.draft,'blue','draft'],['안정 상태 선언',model.groups.status.stable,'teal','stable'],['사용 중단 선언',model.groups.status.deprecated,'muted','deprecated'],['상태 확인 불가',model.groups.status.unknown,'amber','unknown']],model.currentCount,'status'));
  const stateDetails=el('details',undefined,'state-details');add(stateDetails,el('summary','현재 상태 분포 자세히'),grid);home.append(stateDetails);
  const lower=el('div',undefined,'lower-grid');
  renderMapSidePanels(lower,model);
  const sources=panel('원문 연결 상태',`현재 지식에 연결된 고유 보존물 ${model.sourceCount}개 / 과거 전용 출처 제외`);
  function sourceRow(label,spec,count){const b=button('',()=>drill(spec,label,'sources'));b.className='source-row';add(b,el('span',label),el('strong',count));sources.append(b);}
  sourceRow('텍스트 읽기 가능',{kind:'source',key:'available'},model.sourceGroups.available.length);
  sourceRow('텍스트 표시 불가',{kind:'source',key:'nontext'},model.sourceGroups.nontext.length);
  sourceRow('보존 원문 미확인',{kind:'source',key:'unavailable'},model.sourceGroups.unavailable.length);
  sourceRow('출처 기록 확인 필요',{kind:'source',key:'provenance'},model.sourceGroups.provenance.length);
  sourceRow('지원하지 않는 연결이 있는 지식',{kind:'unsupported'},model.unsupported.length);
  sourceRow('출처 연결 선언 없는 지식',{kind:'unlinked'},model.unlinked.length);
  if(model.currentRead<model.currentCount)sources.append(el('p',`${model.currentCount-model.currentRead}개 현재 파일을 읽지 못해 원문 연결 현황도 일부 미확인입니다.`,'warning'));
  const sourceDetails=el('details',undefined,'source-records');add(sourceDetails,el('summary','원문 연결 상태 자세히'),sources);lower.append(sourceDetails);
  const recent=panel('최근 기록','작성 시각 선언순 / 읽은 리비전 기준, 과거 기록 포함');
  const help=el('details');add(help,el('summary','시간과 집계 기준'),el('p','생성 메타데이터의 해석 가능한 시각을 정렬합니다. 인증된 생성 시점이나 실제 이용 활동이 아닙니다. 오류가 있거나 시각을 알 수 없는 기록은 정렬에서 제외합니다. 확인 필요 수는 원문 내용의 오류를 뜻하지 않습니다.'));
  recent.append(help);
  for(const {note:n,time} of model.recent.slice(0,6)){
    const row=button('',()=>drill({kind:'record',id:n.id},'최근 기록','body',n.path));row.className='recent-row';
    add(row,el('span',title(n,n.id)),el('span',(n.current?'현재':'이전')+' / '+new Date(time).toLocaleString('ko-KR'),'subtitle'));recent.append(row);
  }
  recent.append(el('p',`시각 미확인 ${model.unknownTime}개 / 정렬 가능한 ${model.recent.length}개 중 최대 6개 표시`,'path'));
  if(!model.recent.length)recent.append(el('p','정렬 가능한 작성 시각 선언이 없습니다. 활동이 없었다는 뜻은 아닙니다.'));
  lower.append(recent);home.append(lower);
}

function mapGraph() { return KnowledgeMap.model(data); }
function mapTopicOptions(select,graph) {
  select.replaceChildren();const all=el('option','모든 주제');all.value='';select.append(all);
  const topics=[...new Set([...graph.nodes.values()].map(n=>n.topic))].sort((a,b)=>String(a).localeCompare(String(b),'ko'));
  for(const topic of topics){const o=el('option',topic===null?'주제 미지정':topic);o.value=JSON.stringify(topic);select.append(o);}
  if(topicFilter && ![...select.options].some(o=>o.value===topicFilter)){const o=el('option',(JSON.parse(topicFilter)??'주제 미지정')+' (현재 없음)');o.value=topicFilter;select.append(o);}
  select.value=topicFilter;
}
function updateMapFilters() {
  reconcileSelection();renderList();renderDetail();renderHome();
}
function resetMap() {
  drillSpec=null;topicFilter='';mapFocus=null;mapHops=0;mapViewport={x:0,y:0,w:1000,h:600};
  for(const id of ['query','status','fresh','review'])$(id).value='';
  $('drill-banner').hidden=true;updateMapFilters();
}
function selectMapNode(id,focus=false) {
  if(!matchingIds().includes(id))return;
  mapSelected=id;if(mapHops)mapFocus=id;selected=id;revision=data.current[id];historical=false;
  renderList();renderDetail();renderHome();
  if(focus){const node=[...document.querySelectorAll('.map-node')].find(n=>n.dataset.id===id);node?.focus();}
}
function svgElement(name,attributes={},text) {
  const e=document.createElementNS('http://www.w3.org/2000/svg',name);
  for(const [key,value] of Object.entries(attributes))e.setAttribute(key,String(value));
  if(text!==undefined)e.textContent=text;return e;
}
function renderMapHome(home) {
  const graph=mapGraph(),ids=matchingIds(),visible=new Set(ids);
  if(!mapSelected || !visible.has(mapSelected))mapSelected=visible.has(selected)?selected:ids.slice().sort((a,b)=>graph.nodes.get(b)?.neighbors.size-graph.nodes.get(a)?.neighbors.size || a.localeCompare(b))[0]||null;
  const key=JSON.stringify([[...graph.nodes.keys()],graph.edges.map(e=>[e.from,e.to,e.kind])]);
  if(layoutCache.key!==key)layoutCache={key,positions:KnowledgeMap.positions(graph)};
  const options=$('topic');mapTopicOptions(options,graph);
  const section=el('section',undefined,'map-workspace');section.setAttribute('aria-label','현재 지식 지도');
  const map=el('div',undefined,'map-panel');
  const heading=el('div',undefined,'map-heading');
  add(heading,add(el('div'),el('p','KNOWLEDGE OBSERVATORY','eyebrow'),el('h2','연결에서 생각을 찾아보세요')),el('span',`${ids.length} / ${graph.nodes.size}개 현재 지식`,'map-count'));
  map.append(heading);
  const filters=el('div',undefined,'map-filters');
  const search=el('input');search.id='map-query';search.type='search';search.maxLength=200;search.placeholder='제목이나 본문에서 찾기';search.value=$('query').value;
  search.oninput=()=>{const start=search.selectionStart;$('query').value=search.value;updateMapFilters();$('map-query').focus();$('map-query').setSelectionRange(start,start);};
  const topic=el('select');topic.id='map-topic';mapTopicOptions(topic,graph);topic.onchange=()=>{topicFilter=topic.value;mapFocus=null;mapHops=0;updateMapFilters();$('map-topic').focus();};
  add(filters,add(el('label','지식 찾기'),search),add(el('label','선언된 주제'),topic),button('필터 초기화',resetMap));map.append(filters);
  const active=drillSpec?$('drill-label').textContent:'';
  const controls=[active,$('status').value?statusText({status:$('status').value,metadata_errors:[]}):'',$('fresh').value?$('fresh').selectedOptions[0].textContent:'',$('review').value?$('review').selectedOptions[0].textContent:''].filter(Boolean);
  if(controls.length)map.append(el('p','적용 중: '+controls.join(' / '),'map-filter-note'));
  const drawing=el('details',undefined,'map-drawing');drawing.open=!mobile.matches;drawing.append(el('summary','관계 지도 펼치기'));
  const toolbar=el('div',undefined,'map-toolbar');
  function viewport(action){action();const s=$('knowledge-svg');if(s)s.setAttribute('viewBox',`${mapViewport.x} ${mapViewport.y} ${mapViewport.w} ${mapViewport.h}`);}
  function zoom(factor){viewport(()=>{const w=Math.max(250,Math.min(2000,mapViewport.w*factor));const h=w*.6;mapViewport={x:mapViewport.x+(mapViewport.w-w)/2,y:mapViewport.y+(mapViewport.h-h)/2,w,h};});}
  const zoomOut=button('−',()=>zoom(1.25));zoomOut.setAttribute('aria-label','지도 축소');const zoomIn=button('+',()=>zoom(.8));zoomIn.setAttribute('aria-label','지도 확대');
  add(toolbar,zoomOut,zoomIn,button('화면 맞춤',()=>viewport(()=>{mapViewport={x:0,y:0,w:1000,h:600};})));
  for(const [label,dx,dy] of [['왼쪽',-1,0],['위',0,-1],['아래',0,1],['오른쪽',1,0]]){const b=button(label,()=>viewport(()=>{mapViewport.x+=dx*mapViewport.w*.15;mapViewport.y+=dy*mapViewport.h*.15;}));b.className='map-pan';toolbar.append(b);}
  const edges=graph.edges.filter(e=>visible.has(e.from)&&visible.has(e.to));
  toolbar.append(el('span',`${edges.length}개 방향/종류별 관계`,'path'));drawing.append(toolbar);
  const svg=svgElement('svg',{id:'knowledge-svg',viewBox:`${mapViewport.x} ${mapViewport.y} ${mapViewport.w} ${mapViewport.h}`,role:'group','aria-label':'현재 지식 관계 지도. 노드에서 방향키로 이동하고 Enter 또는 Space로 선택하세요.'});
  const defs=svgElement('defs'),marker=svgElement('marker',{id:'relation-arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto-start-reverse'});marker.append(svgElement('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'context-stroke'}));defs.append(marker);svg.append(defs);
  for(const edge of edges.slice(0,600)) {
    const from=layoutCache.positions.get(edge.from),to=layoutCache.positions.get(edge.to),dx=to.x-from.x,dy=to.y-from.y,d=Math.max(1,Math.hypot(dx,dy));
    const radius=10+Math.min(12,Math.sqrt(graph.nodes.get(edge.to).neighbors.size)*3);
    const line=svgElement('line',{x1:from.x,y1:from.y,x2:to.x-dx/d*(radius+4),y2:to.y-dy/d*(radius+4),class:'map-edge'+(edge.declared?' declared':'')+((edge.from===mapSelected||edge.to===mapSelected)?' selected':''),'marker-end':'url(#relation-arrow)'});
    line.append(svgElement('title',{},`${edge.from} → ${edge.to}: ${KnowledgeMap.kindLabel(edge.kind)} (${edge.evidence.length}개 근거)`));svg.append(line);
  }
  const selectedNeighbors=graph.nodes.get(mapSelected)?.neighbors || new Set();
  const labels=KnowledgeMap.labels(graph,layoutCache.positions,ids, mapSelected);
  for(const id of ids) {
    const node=graph.nodes.get(id);if(!node)continue;
    const p=layoutCache.positions.get(id),radius=10+Math.min(12,Math.sqrt(node.neighbors.size)*3),name=title(node.note,id);
    const g=svgElement('g',{class:'map-node'+(id===mapSelected?' active':'')+(selectedNeighbors.has(id)?' neighbor':''),transform:`translate(${p.x} ${p.y})`,role:'button',tabindex:id===mapSelected?0:-1,'aria-label':`${name}, ${node.topic===null?'주제 미지정':node.topic}, 서로 다른 이웃 ${node.neighbors.size}개`,'aria-pressed':String(id===mapSelected),'data-id':id});
    const shape=node.note?svgElement('circle',{r:radius}):svgElement('rect',{x:-radius,y:-radius,width:radius*2,height:radius*2,rx:2});shape.setAttribute('fill',KnowledgeMap.color(node.topic));g.append(shape);
    g.append(svgElement('title',{},`${name}\n${node.topic===null?'주제 미지정':node.topic}\n이웃 ${node.neighbors.size}개${node.note?'':' / 현재 파일 미확인'}`));
    const placement=labels.get(id);
    const label=svgElement('text',{x:placement.x,y:placement.y,'text-anchor':placement.anchor,class:placement.quiet?'quiet-label':''},placement.text);g.append(label);
    g.onclick=()=>selectMapNode(id,true);
    g.onkeydown=event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();selectMapNode(id,true);}else if(['ArrowRight','ArrowDown','ArrowLeft','ArrowUp'].includes(event.key)){event.preventDefault();const step=['ArrowLeft','ArrowUp'].includes(event.key)?-1:1;selectMapNode(ids[(ids.indexOf(id)+step+ids.length)%ids.length],true);}};
    svg.append(g);
  }
  let drag=null;
  svg.onpointerdown=event=>{if(event.target.closest('.map-node'))return;drag={x:event.clientX,y:event.clientY,start:{...mapViewport}};svg.setPointerCapture(event.pointerId);};
  svg.onpointermove=event=>{if(!drag)return;const rect=svg.getBoundingClientRect();mapViewport={...drag.start,x:drag.start.x-(event.clientX-drag.x)*drag.start.w/rect.width,y:drag.start.y-(event.clientY-drag.y)*drag.start.h/rect.height};svg.setAttribute('viewBox',`${mapViewport.x} ${mapViewport.y} ${mapViewport.w} ${mapViewport.h}`);};
  svg.onpointerup=svg.onpointercancel=()=>{drag=null;};drawing.append(svg);map.append(drawing);
  if(!ids.length)map.append(el('p','현재 필터에서 표시할 지식이 없습니다. 필터를 초기화해 범위를 넓힐 수 있습니다.','empty'));
  map.append(el('p','원 크기: 읽은 전체 범위의 서로 다른 이웃 수 / 색: 선언된 주제, 회색은 미지정 / 실선: 본문 링크 / 점선: 선언된 관계 / 화살표: 참조 방향','map-legend'));
  const outside=graph.references.filter(r=>visible.has(r.from)).length;
  const scope=el('details',undefined,'map-scope');add(scope,el('summary',`지도의 읽기 범위: 지도 밖/미확인 참조 ${outside}개${graph.partialNotes.length||graph.invalidIds?' / 일부 미확인':''}`),el('p',`현재로 선택된 개념만 그립니다. 같은 태그, 제목 또는 공통 원문만으로 선을 만들지 않습니다. 과거/원문/외부/자기 참조는 선에서 제외합니다. 형식 또는 읽기 확인이 필요한 노트 ${graph.partialNotes.length}개, 지원하지 않는 ID ${graph.invalidIds}개. 연결선은 최대 600개 표시하며 현재 ${Math.min(edges.length,600)}/${edges.length}개입니다. 필터는 위치를 바꾸지 않습니다.`));map.append(scope);
  const accessible=el('details',undefined,'map-list');add(accessible,el('summary',`키보드로 찾는 지식 목록 (${ids.length})`));
  for(const id of ids){const n=graph.nodes.get(id);if(n){const b=button(title(n.note,id),()=>selectMapNode(id));b.setAttribute('aria-pressed',String(id===mapSelected));accessible.append(b);}}
  map.append(accessible);section.append(map);section.append(mapSummary(graph,visible));home.append(section);
}
function mapSummary(graph,visible) {
  const panel=el('aside',undefined,'map-detail');panel.id='map-detail';panel.tabIndex=-1;
  const node=graph.nodes.get(mapSelected);
  if(!node || !visible.has(node.id)){panel.append(el('h2','선택한 지식'),el('p','표시된 지식을 선택하면 본문 발췌와 실제 연결을 살펴볼 수 있습니다.'));return panel;}
  const n=node.note;add(panel,el('p','SELECTED KNOWLEDGE','eyebrow'),el('h2',title(n,node.id)));
  const topic=el('span',node.topic===null?'주제 미지정':node.topic,'topic-tag');topic.style.borderColor=KnowledgeMap.color(node.topic);panel.append(topic);
  if(!n){panel.append(el('p','현재로 선택됐지만 파일을 읽지 못했습니다. 원문과 이력도 여기서는 미확인입니다.','warning'));return panel;}
  add(panel,el('p',`${statusText(n)} / ${freshText(n)}`,'path'),el('p','본문 발췌','summary-label'));
  const excerpt=n.body.split('\n').filter(line=>line.trim()&&!/^#/.test(line)).join('\n').slice(0,320);panel.append(el('p',excerpt||'표시할 본문이 없습니다.','map-excerpt'));
  const nav=el('div',undefined,'map-detail-actions');for(const [label,target] of [['본문','body'],['원문과 맥락','sources'],['이전 기록','history'],['연결 근거','related']])nav.append(button(label,()=>drill({kind:'record',id:node.id},'지도에서 선택한 기록',target,n.path)));panel.append(nav);
  panel.append(el('p',`서로 다른 이웃 ${node.neighbors.size}개 / 현재 필터에서 ${[...node.neighbors].filter(id=>visible.has(id)).length}개 표시`,'path'));
  const hops=el('div',undefined,'hop-controls');for(const [label,h] of [['전체 범위',0],['1단계 이웃',1],['2단계 이웃',2]]){const b=button(label,()=>{if(h && drillSpec?.kind==='record'){drillSpec=null;$('drill-banner').hidden=true;}mapHops=h;mapFocus=h?node.id:null;updateMapFilters();});b.setAttribute('aria-pressed',String(mapHops===h));hops.append(b);}panel.append(hops);panel.append(el('p','이웃 범위는 현재 필터 안에서 참조 방향을 구분하지 않고 계산합니다.','path'));
  const links=graph.edges.filter(e=>e.from===node.id||e.to===node.id);
  const details=el('details',undefined,'map-evidence');details.open=!mobile.matches;details.append(el('summary',`관찰된 관계 ${links.length}개`));
  for(const edge of links){const other=edge.from===node.id?edge.to:edge.from;const row=el('div',undefined,'neighbor-row');const go=button(title(graph.nodes.get(other).note,other),()=>{mapHops=0;mapFocus=null;selectMapNode(other);});go.disabled=!baseMatchingIds().includes(other);if(go.disabled)go.title='현재 필터 밖의 기록입니다. 필터를 초기화하면 선택할 수 있습니다.';add(row,go,el('p',`${edge.from===node.id?'이 기록에서 참조':'이 기록을 참조'} / ${edge.kind==='본문 링크'?'본문 링크':'선언된 '+KnowledgeMap.kindLabel(edge.kind)}`,'path'));const why=el('details');add(why,el('summary','기록된 근거'),pre(edge.evidence));row.append(why);details.append(row);}
  if(!links.length)details.append(el('p','지원 범위에서 관찰된 선이 없습니다. 의미상 무관하다는 판정은 아닙니다.','path'));panel.append(details);
  const refs=graph.references.filter(r=>r.from===node.id);if(refs.length){const d=el('details');add(d,el('summary',`지도 밖 또는 확인할 참조 ${refs.length}개`),pre(refs.map(r=>r.ref)));panel.append(d);}return panel;
}
function renderMapSidePanels(lower,model) {
  const graph=mapGraph(),topics=new Map();for(const n of graph.nodes.values())topics.set(n.topic,(topics.get(n.topic)||0)+1);
  const box=panel('선언된 주제','읽은 현재 범위 / 자동 분류 없음');
  for(const [topic,count] of [...topics].sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0])))){const b=button('',()=>{topicFilter=JSON.stringify(topic);mapHops=0;mapFocus=null;updateMapFilters();});b.className='source-row';add(b,el('span',topic===null?'주제 미지정':topic),el('strong',count));box.append(b);}lower.append(box);
  const attention=panel('다시 살펴볼 기록',`${model.attention.length}개 / 기한, 형식, 출처 확인`);for(const id of model.attention.slice(0,4))attention.append(button(title(data.notes[data.current[id]],id),()=>drill({kind:'record',id},'확인할 기록','sources')));lower.append(attention);
}
