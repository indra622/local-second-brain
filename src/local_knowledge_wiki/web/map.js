'use strict';
// A projection of delivered references, never a semantic or filesystem search.
const KnowledgeMap = (() => {
  const relationKinds = new Set(['relates_to','depends_on','supersedes','contradicts','supports']);
  const palette = ['#8cc7b5','#b7b9eb','#e3b877','#8ebcdb','#c9b77a','#d7a4ae','#b4c990','#b0b4b8'];
  const own=(object,key)=>Object.prototype.hasOwnProperty.call(object,key);
  const compare=(a,b)=>a<b?-1:a>b?1:0;
  function topic(note) {
    for(const key of ['category','topic']) {
      const value=note?.metadata?.[key];
      if(typeof value==='string' && value.trim() && value.length<=80 && !/[\x00-\x1f\x7f]/.test(value)) return value.trim();
    }
    return null;
  }
  function color(label) {
    if(label===null)return '#9e9a90';
    let hash=2166136261;for(const c of label)hash=Math.imul(hash^c.codePointAt(0),16777619)>>>0;
    return palette[hash%palette.length];
  }
  function model(snapshot) {
    const nodes=new Map(), paths=new Map(), edges=new Map(), references=[], partialNotes=[];
    const ids=Object.keys(snapshot.current).sort(compare);
    let invalidIds=0;
    for(const id of ids) {
      if(!/^[a-z0-9][a-z0-9-]{0,63}$/.test(id) || nodes.size>=100){invalidIds++;continue;}
      const path=snapshot.current[id],note=own(snapshot.notes,path)?snapshot.notes[path]:null;
      nodes.set(id,{id,path,note,topic:topic(note),neighbors:new Set()});paths.set(path,id);
    }
    for(const node of nodes.values()) {
      const n=node.note;
      if(!n || !Array.isArray(n.related) || n.metadata_errors?.length || n.related_partial)partialNotes.push(node.id);
      if(!n || n.metadata_errors?.length || !Array.isArray(n.related))continue;
      for(const ref of n.related) {
        if(!ref || typeof ref!=='object'){references.push({from:node.id,state:'unsupported',ref:null});continue;}
        const kind=ref.kind;
        if(kind!=='본문 링크' && !relationKinds.has(kind)){references.push({from:node.id,state:'unsupported',ref});continue;}
        const to=paths.get(ref.path);
        if(ref.state!=='available' || !to || to===node.id) {
          const state=to===node.id?'self':typeof ref.path==='string' && /^concepts\//.test(ref.path)?'unresolved-concept':'outside-map';
          references.push({from:node.id,state,ref});continue;
        }
        const key=JSON.stringify([node.id,to,kind]);
        if(!edges.has(key))edges.set(key,{from:node.id,to,kind,declared:kind!=='본문 링크',evidence:[]});
        edges.get(key).evidence.push(ref);
        node.neighbors.add(to);nodes.get(to).neighbors.add(node.id);
      }
    }
    return {nodes,edges:[...edges.values()].sort((a,b)=>compare(JSON.stringify([a.from,a.to,a.kind]),JSON.stringify([b.from,b.to,b.kind]))),references,partialNotes,invalidIds};
  }
  function neighborhood(graph,focus,hops,allowed) {
    if(!graph.nodes.has(focus) || !allowed.has(focus))return new Set();
    const result=new Set([focus]);let frontier=[focus];
    for(let h=0;h<hops;h++) {
      const next=[];for(const id of frontier)for(const neighbor of graph.nodes.get(id).neighbors) {
        if(allowed.has(neighbor) && !result.has(neighbor)){result.add(neighbor);next.push(neighbor);}
      }
      frontier=next;
    }
    return result;
  }
  function positions(graph) {
    const ids=[...graph.nodes.keys()].sort(compare),points=new Map();
    if(ids.length===1)return new Map([[ids[0],{x:500,y:300}]]);
    ids.forEach((id,i)=>{const angle=i*2.399963229728653;const radius=65+Math.sqrt(i)*28;points.set(id,{x:Math.cos(angle)*radius,y:Math.sin(angle)*radius});});
    const pairs=new Map();for(const edge of graph.edges){const pair=[edge.from,edge.to].sort(compare);pairs.set(JSON.stringify(pair),pair);}
    // Bounded, deterministic settling. No animation, randomness, timers or live drift.
    for(let step=0;step<180;step++) {
      const forces=new Map(ids.map(id=>[id,{x:-points.get(id).x*.006,y:-points.get(id).y*.006}]));
      for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++) {
        const a=points.get(ids[i]),b=points.get(ids[j]);let dx=a.x-b.x,dy=a.y-b.y;
        if(dx===0&&dy===0){dx=1;dy=.5;}const d2=Math.max(36,dx*dx+dy*dy),d=Math.sqrt(d2),power=4800/d2;
        forces.get(ids[i]).x+=dx/d*power;forces.get(ids[i]).y+=dy/d*power;
        forces.get(ids[j]).x-=dx/d*power;forces.get(ids[j]).y-=dy/d*power;
      }
      for(const [from,to] of pairs.values()) {
        const a=points.get(from),b=points.get(to),dx=b.x-a.x,dy=b.y-a.y,d=Math.max(1,Math.hypot(dx,dy)),power=(d-100)*.018;
        forces.get(from).x+=dx/d*power;forces.get(from).y+=dy/d*power;forces.get(to).x-=dx/d*power;forces.get(to).y-=dy/d*power;
      }
      for(const id of ids){const p=points.get(id),f=forces.get(id);p.x+=Math.max(-5,Math.min(5,f.x));p.y+=Math.max(-5,Math.min(5,f.y));}
    }
    if(!ids.length)return points;
    const xs=[...points.values()].map(p=>p.x),ys=[...points.values()].map(p=>p.y);
    const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
    for(const p of points.values()){p.x=80+(p.x-minX)/Math.max(1,maxX-minX)*840;p.y=60+(p.y-minY)/Math.max(1,maxY-minY)*450;}
    return points;
  }
  function labels(graph,points,ids,focus) {
    const result=new Map(),placed=[],neighbors=graph.nodes.get(focus)?.neighbors||new Set();
    const ordered=ids.slice().sort((a,b)=>(a===focus?-1:b===focus?1:0)||(Number(neighbors.has(b))-Number(neighbors.has(a)))||compare(a,b));
    const overlap=(a,b)=>a.x<b.x+b.w+3&&a.x+a.w+3>b.x&&a.y<b.y+b.h+3&&a.y+a.h+3>b.y;
    const obstacles=ids.map(id=>{const p=points.get(id),r=10+Math.min(12,Math.sqrt(graph.nodes.get(id).neighbors.size)*3)+3;return {x:p.x-r,y:p.y-r,w:r*2,h:r*2};});
    for(const id of ordered) {
      const node=graph.nodes.get(id),p=points.get(id),r=10+Math.min(12,Math.sqrt(node.neighbors.size)*3);
      const full=typeof node.note?.title==='string'&&node.note.title.trim()?node.note.title:id;
      const limit=id===focus?20:13,text=[...full].slice(0,limit).join('')+([...full].length>limit?'…':'');
      const width=[...text].length*12+8,preferred=ids.length<=14||id===focus||neighbors.has(id)||(ids.length<=30&&!node.neighbors.size);
      const right={x:r+8,y:4,anchor:'start'},left={x:-r-8,y:4,anchor:'end'},top={x:0,y:-r-12,anchor:'middle'},bottom={x:0,y:r+22,anchor:'middle'};
      const sides=p.x<200?[right,left]:p.x<500?[left,right]:p.x>800?[left,right]:[right,left];
      const candidates=id===focus?[top,...sides,bottom]:[...sides,top,bottom];
      let chosen=null;
      if(preferred)for(const c of candidates) {
        const box={x:p.x+c.x-(c.anchor==='end'?width:c.anchor==='middle'?width/2:0),y:p.y+c.y-14,w:width,h:20};
        if(box.x<6||box.x+box.w>994||box.y<4||box.y+box.h>596||placed.some(b=>overlap(box,b))||obstacles.some(b=>overlap(box,b)))continue;
        chosen=c;placed.push(box);break;
      }
      result.set(id,{...(chosen||candidates[0]),text,quiet:!chosen&&id!==focus});
    }
    return result;
  }
  const kindLabel=kind=>({'본문 링크':'본문 링크',relates_to:'관련 관계',depends_on:'의존 관계',supersedes:'대체 관계',contradicts:'상충 관계',supports:'뒷받침 관계'})[kind]||'미지원 관계';
  return {model,topic,color,positions,neighborhood,kindLabel,labels};
})();
