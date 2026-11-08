import React,{useState,useMemo,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {Theme} from '@astryxdesign/core/theme';
import {Button} from '@astryxdesign/core/Button';
import {TextInput} from '@astryxdesign/core/TextInput';
import {Badge} from '@astryxdesign/core/Badge';
import {Link} from '@astryxdesign/core/Link';
import {neutralTheme} from '@astryxdesign/theme-neutral/built';
import {KnowledgeMap} from './shared-map.mjs';
import {overview,eligible,classicDestination} from './selectors.mjs';
import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import '@astryxdesign/theme-neutral/theme.css';
import './style.css';

function MapView({graph,ids,selected,onSelect}){
  const points=useMemo(()=>KnowledgeMap.positions(graph),[graph]);
  const visible=new Set(ids),labels=KnowledgeMap.labels(graph,points,ids,selected);
  const edges=graph.edges.filter(e=>visible.has(e.from)&&visible.has(e.to));
  return <section className="ax-map panel" aria-label="현재 지식 관계 지도">
    <div className="panel-head"><h2>현재 지식 지도</h2><span>{ids.length} / {graph.nodes.size}개</span></div>
    <p className="muted">실제 현재 링크와 관계 선언만 표시합니다.</p>
    <details className="drawing" open={!window.matchMedia('(max-width:800px)').matches}><summary>지도 펼치기</summary>
      <svg viewBox="0 0 1000 600" role="group" aria-label="현재 노트 지도. 방향키로 이동, Enter 또는 Space로 선택">
        <defs><marker id="ax-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="context-stroke"/></marker></defs>
        {edges.slice(0,600).map((edge,i)=>{const a=points.get(edge.from),b=points.get(edge.to),d=Math.max(1,Math.hypot(b.x-a.x,b.y-a.y)),r=14+Math.min(12,Math.sqrt(graph.nodes.get(edge.to).neighbors.size)*3);
          return <line key={i} x1={a.x} y1={a.y} x2={b.x-(b.x-a.x)/d*r} y2={b.y-(b.y-a.y)/d*r} className={'edge'+(edge.declared?' declared':'')+([edge.from,edge.to].includes(selected)?' active':'')} markerEnd="url(#ax-arrow)"><title>{KnowledgeMap.kindLabel(edge.kind)}</title></line>;})}
        {ids.map(id=>{const node=graph.nodes.get(id),p=points.get(id),r=10+Math.min(12,Math.sqrt(node.neighbors.size)*3),label=labels.get(id),name=typeof node.note?.title==='string'?node.note.title:id;
          return <g key={id} data-id={id} className={'graph-node'+(id===selected?' chosen':'')} transform={`translate(${p.x} ${p.y})`} role="button" tabIndex={id===selected?0:-1} aria-label={`${name}, 이웃 ${node.neighbors.size}개`} aria-pressed={id===selected} onClick={()=>onSelect(id)} onKeyDown={e=>{
            if(['Enter',' '].includes(e.key)){e.preventDefault();onSelect(id);}
            if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();const step=['ArrowLeft','ArrowUp'].includes(e.key)?-1:1;const next=ids[(ids.indexOf(id)+step+ids.length)%ids.length];onSelect(next);requestAnimationFrame(()=>document.querySelector(`.graph-node[data-id="${next}"]`)?.focus());}
          }}>{node.note?<circle r={r} fill={KnowledgeMap.color(node.topic)}/>:<rect x={-r} y={-r} width={r*2} height={r*2} fill={KnowledgeMap.color(node.topic)}/>}
          <title>{name}</title><text x={label.x} y={label.y} textAnchor={label.anchor} className={label.quiet?'quiet':''}>{label.text}</text></g>;})}
      </svg>
    </details>
    {!ids.length&&<p role="status">현재 조건에 일치하는 노트가 없습니다.</p>}
    <p className="muted legend">실선: 본문 링크 / 점선: 관계 선언</p>
    <p className="muted legend">원 크기: 관찰 이웃 수 / 색: 선언된 주제 / 사각형: 현재 파일 미확인</p>
    <details><summary>범위와 미확인 참조</summary><p>현재 범위의 지도 밖/미확인 참조 {graph.references.filter(r=>visible.has(r.from)).length}개. 읽기/형식 확인이 필요한 현재 노트 {graph.partialNotes.length}개. 선 {Math.min(600,edges.length)}/{edges.length}개 표시. 동일 주제나 원문으로 선을 추정하지 않습니다.</p></details>
  </section>;
}
function App(){
  const [data,setData]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[query,setQuery]=useState(''),[topic,setTopic]=useState(''),[selected,setSelected]=useState(null);
  async function refresh(){setLoading(true);try{const response=await fetch('../api/snapshot',{cache:'no-store',signal:AbortSignal.timeout(20000)});const next=await response.json();if(!response.ok)throw Error(next.error||'읽기 실패');if(!next.current||!next.notes||!next.sources)throw Error('응답 형식 확인 불가');setData(next);setError('');}catch(e){setError('갱신 실패. 마지막 성공 화면은 유지합니다. '+e.message);}finally{setLoading(false);}}
  useEffect(()=>{refresh();},[]);
  const graph=useMemo(()=>data?KnowledgeMap.model(data):null,[data]);
  const ids=useMemo(()=>graph?eligible(data,graph,query,topic):[],[data,graph,query,topic]);
  const active=ids.includes(selected)?selected:ids[0]||null,node=graph?.nodes.get(active),note=node?.note;
  const topics=graph?[...new Set([...graph.nodes.values()].map(n=>n.topic))].sort((a,b)=>String(a).localeCompare(String(b),'ko')):[];
  if(topic&&!topics.some(t=>JSON.stringify(t)===topic))topics.push(JSON.parse(topic));
  const stats=data?overview(data):null;
  const title=n=>typeof n?.title==='string'&&n.title.trim()?n.title:active;
  return <div className="astryx-app">
    <header><div className="brand"><span>L</span><div>Local Second Brain<small>Astryx 비교 홈</small></div></div><Link href="../">기존 홈으로 돌아가기</Link><Button label="새로 읽기" onClick={refresh} isLoading={loading}/></header>
    <main><div className="title-row"><div><Badge label="선택적 비교 화면" variant="neutral"/><h1>지식 현황, 다른 구성으로</h1></div><p className="muted">기존 홈과 같은 읽기 전용 데이터</p></div>
      {error&&<p className="error" role="alert">{error}</p>}
      <p className="snapshot" role="status">{data?`${data.bundle} / 마지막 성공 ${new Date(data.completed_at).toLocaleString('ko-KR')}${data.partial?' / 일부 기록 미확인':''}`:'아직 성공한 스냅샷이 없습니다.'}</p>
      {stats&&<>
        <section className="stats" aria-label="실제 스냅샷 현황">{[['현재 지식',stats.current,`${stats.unread}개 현재 파일 미확인`],['읽은 리비전',stats.revisions,'과거 기록 포함'],['확인 기한 지남',stats.overdue,'판정 가능한 현재 기록'],['기한 미지정 / 미확인',stats.unknown,'형식/파일 미확인 포함']].map(([label,value,sub])=><article className="panel" key={label}><span>{label}</span><strong>{value}</strong><small>{sub}</small></article>)}</section>
        <section className="filters panel" aria-label="검색과 주제 필터"><TextInput label="현재 제목과 본문에서 찾기" value={query} onChange={setQuery} placeholder="찾고 싶은 생각" containerClassName="search" type="search"/><label>선언된 주제<select value={topic} onChange={e=>setTopic(e.target.value)}><option value="">모든 주제</option>{topics.map(t=><option key={JSON.stringify(t)} value={JSON.stringify(t)}>{t===null?'주제 미지정 / 미확인':t}</option>)}</select></label><Button label="필터 초기화" variant="ghost" onClick={()=>{setQuery('');setTopic('');}}/></section>
        <div className="workspace"><MapView graph={graph} ids={ids} selected={active} onSelect={setSelected}/>
          <aside className="selection panel" aria-label="선택한 현재 기록"><span className="eyebrow">선택한 현재 지식</span><h2>{node?title(note):'일치하는 지식 없음'}</h2>
            {node&&<Badge label={node.topic===null?'주제 미지정 / 미확인':node.topic} variant="teal"/>}
            {node&&!note&&<p className="error">현재 파일을 읽지 못했습니다. 원문과 이력도 미확인입니다.</p>}
            {note&&<><p className="muted">{note.metadata_errors.length?'형식 확인 필요':note.status==='draft'?'초안':note.status==='stable'?'안정 상태 선언':note.status==='deprecated'?'사용 중단 선언':'상태 미확인'} / {note.metadata_errors.length?'기한 판정 불가':note.stale===true?'확인 기한 지남':note.stale===false?'확인 기한 전':'확인 기한 없음'}</p>
              <h3>본문 발췌</h3><p className="excerpt">{note.body.split(/\n\s*\n/).find(block=>block.trim()&&!block.trim().startsWith('#'))?.slice(0,350)||'표시할 본문 없음'}</p>
              <nav className="detail-links" aria-label="기존 탐색으로 이동">{[['본문','body'],['원문과 맥락','sources'],['이전 기록','history'],['연결 근거','related']].map(([label,panel])=><Link key={panel} href={classicDestination(data,active,panel)}>{label} ↗</Link>)}</nav><p className="muted">위 링크는 기존 탐색 화면의 정확한 기록을 엽니다.</p>
              <p className="muted">이웃 {node.neighbors.size}개 / 검토 선언 {note.metadata_errors.length?'미확인':note.verified&&(!Array.isArray(note.verified)||note.verified.length)?'있음':'없음'}</p></>}
            <details><summary>선언과 표시의 의미</summary><p>작성/검토 주체와 시각은 인증된 사실이 아닙니다. 본문, 출처와 미확인은 기존 탐색에서 비교할 수 있습니다. 이 비교 홈은 어두운 모드이며 기존 홈의 모든 필터와 기능을 옮기지는 않았습니다.</p></details>
          </aside></div>
        <section className="panel note-list"><h2>같은 범위의 지식 목록</h2><p className="muted">지도 대신 키보드와 목록으로 선택할 수 있습니다. {ids.length}개 표시.</p><div>{ids.map(id=><Button key={id} label={typeof graph.nodes.get(id).note?.title==='string'?graph.nodes.get(id).note.title:id} variant={id===active?'secondary':'ghost'} onClick={()=>setSelected(id)} aria-pressed={id===active}/>)}</div></section>
      </>}
      <footer>로컬 비교 화면 / 자동 갱신, 편집, 수집과 모델 호출 없음 / <Link href="./notices.txt">구성요소 라이선스</Link></footer>
    </main>
  </div>;
}
createRoot(document.getElementById('root')).render(<Theme theme={neutralTheme} mode="dark"><App/></Theme>);
