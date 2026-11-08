// Real snapshot JSON from Python, consumed by the actual production recent model.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const nodes={};const node=id=>nodes[id]??={value:'',hidden:true,addEventListener(){},setAttribute(){}};
const box={document:{getElementById:node},window:{matchMedia:()=>({matches:false,addEventListener(){}})},AbortSignal,console,input};
vm.createContext(box);
const code=fs.readFileSync(path.join(__dirname,'../src/local_knowledge_wiki/web/app.js'),'utf8').replace('\nrefresh();\n','\n');
vm.runInContext(code,box);
const model=vm.runInContext('homeModel(input.snapshot)',box);
const recent=new Map(model.recent.map(item=>[item.note.id,item.time]));
for(const [id,normalized] of Object.entries(input.expected)){
  if(normalized===null)assert.equal(recent.has(id),false,id);
  else {assert.equal(recent.has(id),true,id);assert.equal(recent.get(id),Date.parse(normalized),id);}
}
assert.equal(model.unknownTime,Object.values(input.expected).filter(value=>value===null).length);
assert.equal(recent.get('timestamp-quoted'),recent.get('timestamp-unquoted'));
assert.equal(recent.get('timestamp-offset'),recent.get('timestamp-negative'));
assert.equal(recent.get('timestamp-fraction'),recent.get('timestamp-quoted-fraction'));
console.log('PASS: actual YAML snapshot transport reaches recent with equivalent instants; invalid/naive declarations remain unknown');
