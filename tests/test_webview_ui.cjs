// Pure snapshot aggregation and refresh transitions; browser rendering is checked separately.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes={};const node=id=>nodes[id]??={value:'',hidden:true,addEventListener(){},setAttribute(){}};
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
  const last=vm.runInContext('data',box);box.fetch=async()=>{throw Error('test failure')};await vm.runInContext('refresh()',box);assert.equal(vm.runInContext('data',box),last);
  assert.equal(nodes.error.hidden,false);
  console.log('PASS: current/all-revision aggregation, unknown/missing states, unique current sources, empty snapshot, fallback reset, history retention, refresh failure retention');
})().catch(e=>{console.error(e);process.exitCode=1});
