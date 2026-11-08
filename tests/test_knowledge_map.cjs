const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const box={};vm.createContext(box);vm.runInContext(fs.readFileSync('src/local_knowledge_wiki/web/map.js','utf8'),box);
const path=id=>`concepts/${id}/r000001.md`;
const note=(id,related=[],meta={})=>({id,path:path(id),metadata:meta,metadata_errors:[],related,related_partial:false,source_ids:[],source_refs:[],body:'synthetic',status:'draft',stale:null,verified:null});
const link=(id,kind='본문 링크')=>({path:path(id),kind,state:'available',line:1,resource:path(id)});
const snapshot={current:{a:path('a'),b:path('b'),constructor:path('constructor'),missing:path('missing'),island:path('island')},notes:{},sources:{}};
snapshot.notes[path('a')]=note('a',[link('b'),link('b'),link('constructor','supports'),{...link('b'),path:'concepts/b/r000002.md'},link('absent'),{kind:'본문 링크',path:'sources/input/content.raw',state:'unchecked'},{kind:'made-up',path:path('island'),state:'available'},link('a')],{category:'독서'});
snapshot.notes[path('b')]=note('b',[link('constructor')],{category:'독서'});
snapshot.notes[path('constructor')]=note('constructor',[],{topic:'설계'});
snapshot.notes[path('island')]=note('island',[],{tags:['독서']});
box.input=snapshot;
const graph=vm.runInContext('KnowledgeMap.model(input)',box);
assert.equal(graph.nodes.size,5);assert.equal(graph.edges.length,3);assert.equal(graph.edges[0].evidence.length,2);
assert.equal(graph.nodes.get('a').neighbors.size,2);assert.equal(graph.nodes.get('constructor').neighbors.size,2);assert.equal(graph.nodes.get('island').neighbors.size,0);
assert.equal(graph.references.length,5);assert.equal(graph.partialNotes.length,1);assert.equal(graph.nodes.get('island').topic,null);
box.graph=graph;
const positions=vm.runInContext('KnowledgeMap.positions(graph)',box);
const labels=vm.runInContext("KnowledgeMap.labels(graph,KnowledgeMap.positions(graph),[...graph.nodes.keys()],'a')",box);
assert.equal(labels.get('a').quiet,false);for(const value of labels.values())assert.ok([...value.text].length<=21);
assert.equal(JSON.stringify([...labels]),JSON.stringify([...vm.runInContext("KnowledgeMap.labels(graph,KnowledgeMap.positions(graph),[...graph.nodes.keys()],'a')",box)]));
const reordered={...snapshot,current:Object.fromEntries(Object.entries(snapshot.current).reverse())};box.reordered=reordered;
const second=vm.runInContext('KnowledgeMap.positions(KnowledgeMap.model(reordered))',box);
assert.equal(JSON.stringify([...positions]),JSON.stringify([...second]));
assert.equal(vm.runInContext("KnowledgeMap.color('독서')",box),vm.runInContext("KnowledgeMap.color('독서')",box));
assert.equal(vm.runInContext('KnowledgeMap.topic({metadata:{category:["bad"],topic:"선언"}})',box),'선언');
assert.equal(vm.runInContext('KnowledgeMap.model({current:{},notes:{}}).nodes.size',box),0);
assert.equal(vm.runInContext('KnowledgeMap.positions(KnowledgeMap.model({current:{a:"p"},notes:{}})).get("a").x',box),500);
const scope=vm.runInContext("KnowledgeMap.neighborhood(graph,'a',1,new Set(['a','b','constructor','island']))",box);assert.equal(scope.size,3);
assert.equal(vm.runInContext("KnowledgeMap.neighborhood(graph,'a',2,new Set(['a','island'])).size",box),1);
const invalid={...snapshot,current:{'../escape':'outside',constructor:path('constructor')}};box.invalid=invalid;assert.equal(vm.runInContext('KnowledgeMap.model(invalid).invalidIds',box),1);
const chain={current:{a:path('a'),b:path('b'),c:path('c')},notes:{[path('a')]:note('a',[link('b')]),[path('b')]:note('b',[link('c')]),[path('c')]:note('c')}};box.chain=chain;
assert.equal(vm.runInContext("KnowledgeMap.neighborhood(KnowledgeMap.model(chain),'a',1,new Set(['a','b','c'])).size",box),2);
assert.equal(vm.runInContext("KnowledgeMap.neighborhood(KnowledgeMap.model(chain),'a',2,new Set(['a','b','c'])).size",box),3);
assert.equal(vm.runInContext("KnowledgeMap.neighborhood(KnowledgeMap.model(chain),'a',2,new Set(['a','c'])).size",box),1);
const hundred={current:Object.fromEntries(Array.from({length:100},(_,i)=>['n'+i,path('n'+i)])),notes:{}};box.hundred=hundred;
const settled=vm.runInContext('KnowledgeMap.positions(KnowledgeMap.model(hundred))',box);
assert.equal(settled.size,100);for(const p of settled.values()){assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.y));assert.ok(p.x>=80&&p.x<=920&&p.y>=60&&p.y<=510);}
// Malformed metadata cannot donate raw frontmatter links to the map.
snapshot.notes[path('a')].metadata_errors=['invalid'];box.input=snapshot;assert.equal(vm.runInContext('KnowledgeMap.model(input).edges.length',box),1);snapshot.notes[path('a')].metadata_errors=[];
// Existing filter/selection code is exercised with the real graph model, no rendered DOM.
const nodes={};box.document={getElementById:id=>nodes[id]??={value:'',addEventListener(){},setAttribute(){},focus(){},scrollIntoView(){}}};box.window={matchMedia:()=>({matches:false,addEventListener(){}})};box.AbortSignal=AbortSignal;
vm.runInContext(fs.readFileSync('src/local_knowledge_wiki/web/app.js','utf8').replace('\nrefresh();\n','\n'),box);
vm.runInContext('data=input;selected="a";renderList=()=>{};renderDetail=()=>{};renderHome=()=>{};showView=()=>{}',box);
vm.runInContext('topicFilter=JSON.stringify("독서");reconcileSelection()',box);assert.deepEqual(Array.from(vm.runInContext('matchingIds()',box)),['a','b']);
vm.runInContext('topicFilter="";mapHops=1;mapFocus="b";reconcileSelection()',box);assert.deepEqual(Array.from(vm.runInContext('matchingIds()',box)),['a','b','constructor']);
vm.runInContext("selectMapNode('a')",box);assert.equal(vm.runInContext('mapFocus',box),'a');
vm.runInContext("mapHops=0;mapFocus=null;historical=true;revision='old';data.notes.old={id:'a'}",box);
const original=vm.runInContext('data',box);box.fetch=async()=>{throw Error('synthetic refresh failure')};
(async()=>{
 await vm.runInContext('refresh()',box);assert.equal(vm.runInContext('data',box),original);assert.equal(nodes.error.hidden,false);
 // Successful structure movement resets a vanished neighborhood anchor and selection.
 box.next={current:{island:path('island')},notes:{[path('island')]:note('island')},sources:{},diagnostics:[],completed_at:new Date().toISOString(),scanned_at:new Date().toISOString()};
 box.fetch=async()=>({ok:true,json:async()=>box.next});vm.runInContext("mapHops=2;mapFocus='a'",box);await vm.runInContext('refresh()',box);
 assert.equal(vm.runInContext('mapHops',box),0);assert.equal(vm.runInContext('selected',box),'island');assert.equal(vm.runInContext('historical',box),false);
 console.log('PASS: delivered edges/evidence, no inferred/shared/historical edges, degree, topics, constructor/missing/invalid nodes, deterministic layout, 0/1 nodes, filtered hops, topic filter and refresh/failure selection');
})().catch(e=>{console.error(e);process.exitCode=1});
