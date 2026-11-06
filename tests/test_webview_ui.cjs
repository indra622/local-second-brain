// Pure snapshot aggregation and refresh transitions; browser rendering is checked separately.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes={};const node=id=>nodes[id]??={value:'',hidden:true,addEventListener(){},setAttribute(){},scrollIntoView(){},focus(){}};
const box={document:{getElementById:node},window:{matchMedia:()=>({matches:false,addEventListener(){}})},AbortSignal,console};
vm.createContext(box);
const code=fs.readFileSync('src/local_knowledge_wiki/web/app.js','utf8').replace('\nrefresh();\n','\n');
vm.runInContext(code,box);
const note=(id,extra={})=>({id,path:id+'1',status:'draft',metadata_errors:[],metadata:{},source_ids:[],source_refs:[],stale:null,stale_after:null,verified:null,generated:{at:'2026-11-06T00:00:00Z'},...extra});
const snapshot={current:{a:'a1',b:'b1',c:'c1',d:'d1'},notes:{a1:note('a',{status:'stable',stale:true,verified:[{by:'process:test'}],source_ids:['shared'],source_refs:[{state:'canonical-binding'}]}),b1:note('b',{source_ids:['shared'],source_refs:[{state:'canonical-binding'}]}),c1:note('c',{metadata_errors:['invalid'],generated:{at:'not-time'}}),old:note('a',{path:'old',source_ids:['historical-only']})},sources:{shared:{state:'available',hash_matches_declaration:true},'historical-only':{state:'unavailable'}},diagnostics:[{state:'missing-current'}],partial:true};
box.input=snapshot;
let m=vm.runInContext('homeModel(input)',box);
assert.equal(m.currentCount,4);assert.equal(m.currentRead,3);assert.equal(m.revisions,4);
assert.equal(m.groups.deadline.overdue.length,1);assert.equal(m.groups.deadline.none.length,1);assert.equal(m.groups.deadline.invalid.length,1);assert.equal(m.groups.deadline.missing.length,1);
assert.equal(m.groups.review.declared.length,1);assert.equal(m.groups.review.none.length,1);assert.equal(m.groups.review.unknown.length,2);
assert.equal(m.sourceCount,1);assert.equal(m.sourceGroups.available.length,1);assert.equal(m.attention.length,3);assert.equal(m.unknownTime,1);
box.input={current:{},notes:{},sources:{},diagnostics:[],partial:false};m=vm.runInContext('homeModel(input)',box);assert.equal(m.currentCount,0);assert.equal(m.revisions,0);
vm.runInContext('renderList=()=>{};renderDetail=()=>{};renderHome=()=>{};showView=()=>{}',box);
const snap=r=>({bundle:'synthetic',current:{b:r},notes:{[r]:note('b',{path:r})},completed_at:new Date().toISOString(),scanned_at:new Date().toISOString(),diagnostics:[]});
async function update(next){box.fetch=async()=>({ok:true,json:async()=>next});await vm.runInContext('refresh()',box);return vm.runInContext('({selected,revision,historical})',box);}
(async()=>{
  vm.runInContext("selected='a';revision='a-old';historical=true",box);
  let state=await update(snap('b1'));assert.equal(state.revision,'b1');assert.equal(state.historical,false);
  let next=snap('b2');next.notes.b1=note('b',{path:'b1'});state=await update(next);assert.equal(state.revision,'b2');assert.equal(state.historical,false);
  vm.runInContext("revision='b1';historical=true",box);state=await update(next);assert.equal(state.revision,'b1');
  // Legal IDs must not collide with Object.prototype, including after removal.
  box.input={current:{constructor:'c1'},notes:{c1:note('constructor',{source_ids:['constructor'],source_refs:[{state:'canonical-binding'}]})},sources:{constructor:{state:'available',hash_matches_declaration:true}}};
  const legal=vm.runInContext('homeModel(input)',box);
  assert.equal(legal.sourceCount,1);assert.deepEqual(Array.from(legal.sourceOwners.constructor),['constructor']);
  vm.runInContext("selected='constructor';revision='c-old';historical=true",box);
  state=await update(snap('b1'));assert.equal(state.selected,'b');assert.equal(state.historical,false);
  next=snap('b2');next.notes.b1=note('b',{path:'b1'});assert.equal((await update(next)).revision,'b2');
  // Every home category is evaluated from each new snapshot, not captured IDs.
  const pair=(a,b,sources={})=>({bundle:'synthetic',current:{a:'a1',b:'b1'},notes:{a1:note('a',a),b1:note('b',b)},sources,diagnostics:[],completed_at:new Date().toISOString(),scanned_at:new Date().toISOString()});
  const cases=[
    [{kind:'group',family:'deadline',key:'overdue'},{stale:true},{stale:false},{}],
    [{kind:'group',family:'review',key:'declared'},{verified:[{by:'process:test'}]},{verified:null},{}],
    [{kind:'group',family:'status',key:'draft'},{status:'draft'},{status:'stable'},{}],
    [{kind:'attention'},{stale:true},{stale:false},{}],
    [{kind:'unlinked'},{source_refs:[]},{source_refs:[{state:'canonical-binding'}]},{}],
    [{kind:'unsupported'},{source_refs:[{state:'unsupported-or-unknown'}]},{source_refs:[{state:'canonical-binding'}]},{}]
  ];
  for(const key of ['available','nontext','unavailable','provenance']) {
    const source=key==='available'?{state:'available',hash_matches_declaration:true}:key==='nontext'?{state:'non-utf8',hash_matches_declaration:true}:key==='unavailable'?{state:'unavailable'}:{state:'available',hash_matches_declaration:false};
    const other=key==='available'?{state:'unavailable'}:{state:'available',hash_matches_declaration:true};
    cases.push([{kind:'source',key},{source_ids:['one'],source_refs:[{state:'canonical-binding'}]},{source_ids:['two'],source_refs:[{state:'canonical-binding'}]},{one:source,two:other}]);
  }
  for(const [spec,a,b,sources] of cases) {
    box.spec=spec;vm.runInContext('drillSpec=spec;selected=null;historical=false',box);
    await update(pair(a,b,sources));assert.deepEqual(Array.from(vm.runInContext('matchingIds()',box)),['a'],JSON.stringify(spec));
    const nextSources=Object.keys(sources).length?{one:sources.two,two:sources.one}:sources;
    const changed=Object.keys(sources).length?pair(a,b,nextSources):pair(b,a,sources);
    state=await update(changed);assert.deepEqual(Array.from(vm.runInContext('matchingIds()',box)),['b'],JSON.stringify(spec));assert.equal(state.selected,'b');assert.equal(state.revision,'b1');
  }
  vm.runInContext("drillSpec={kind:'group',family:'deadline',key:'overdue'}",box);
  state=await update(pair({stale:false},{stale:false}));assert.equal(state.selected,null);assert.equal(state.revision,null);
  // The manual controls remain an intersection with the live category.
  nodes.status.value='stable';state=await update(pair({stale:true,status:'draft'},{stale:false,status:'stable'}));assert.equal(state.selected,null);assert.equal(nodes.status.value,'stable');
  state=await update(pair({stale:true,status:'stable'},{stale:false}));assert.equal(state.selected,'a');nodes.status.value='';
  vm.runInContext("drillSpec={kind:'record',id:'a'};selected='a';revision='a-old';historical=true",box);
  const explicit=pair({stale:false},{stale:true});explicit.notes['a-old']=note('a',{path:'a-old'});
  state=await update(explicit);assert.equal(state.revision,'a-old');assert.equal(state.historical,true);
  const last=vm.runInContext('data',box);box.fetch=async()=>{throw Error('test failure')};await vm.runInContext('refresh()',box);assert.equal(vm.runInContext('data',box),last);
  assert.equal(nodes.error.hidden,false);
  console.log('PASS: current/all-revision aggregation, unknown/missing states, unique current sources, empty snapshot, constructor IDs/removal, all live category families, coherent empty detail, manual filters, fallback reset, explicit record/history retention, refresh failure retention');
})().catch(e=>{console.error(e);process.exitCode=1});
