import * as esbuild from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const dist='dist';fs.mkdirSync(dist,{recursive:true});
try{
  const result=await esbuild.build({entryPoints:['src/main.jsx'],bundle:true,minify:true,format:'esm',platform:'browser',target:['chrome120','firefox128','safari18'],outfile:dist+'/app.js',metafile:true,legalComments:'none',define:{'process.env.NODE_ENV':'"production"'}});
  fs.writeFileSync('metafile.json',JSON.stringify(result.metafile));
  fs.copyFileSync('index.html',dist+'/index.html');
  const packages=new Map();
  for(const output of Object.values(result.metafile.outputs))for(const [file,value] of Object.entries(output.inputs)){
    if(!value.bytesInOutput||!file.includes('node_modules/'))continue;
    let dir=path.dirname(path.resolve(file));
    while(dir.includes(path.sep+'node_modules')){
      const manifest=path.join(dir,'package.json');
      if(fs.existsSync(manifest)){const meta=JSON.parse(fs.readFileSync(manifest));packages.set(meta.name,{dir,meta});break;}
      dir=path.dirname(dir);
    }
  }
  const notices=[];
  for(const [name,{dir,meta}] of [...packages].sort(([a],[b])=>a.localeCompare(b))){
    notices.push(`${name}@${meta.version} (${meta.license||'see license'})`);
    const license=fs.readdirSync(dir).filter(n=>/^licen[sc]e(?:\.|$)|^copying(?:\.|$)|^notice(?:\.|$)/i.test(n)&&fs.statSync(path.join(dir,n)).isFile());
    if(!license.length){if(name.startsWith('@astryxdesign/'))notices.push(fs.readFileSync('licenses/astryx.txt','utf8'));else if(name==='@stylexjs/stylex')notices.push(fs.readFileSync('licenses/stylex.txt','utf8'));else throw Error('Missing license text for bundled '+name);}
    for(const file of license)notices.push(fs.readFileSync(path.join(dir,file),'utf8'));
  }
  fs.writeFileSync(dist+'/notices.txt',notices.join('\n\n----------------\n\n').trimEnd()+'\n');
  const sourceFiles=['package.json','package-lock.json','build.mjs','index.html','test.mjs','licenses/astryx.txt','licenses/stylex.txt',...fs.readdirSync('src').sort().map(n=>'src/'+n)];
  const manifest={schema:1,packages:Object.fromEntries([...packages].map(([name,{meta}])=>[name,meta.version]).sort()),source:Object.fromEntries(sourceFiles.map(n=>[n,hash(n)])),assets:Object.fromEntries(['index.html','app.js','app.css','notices.txt'].map(n=>[n,{bytes:fs.statSync(dist+'/'+n).size,sha256:hash(dist+'/'+n)}]))};
  fs.writeFileSync(dist+'/build-manifest.json',JSON.stringify(manifest,null,2)+'\n');
  fs.writeFileSync('metafile.json',JSON.stringify(result.metafile));
  console.log(JSON.stringify({packages:manifest.packages,assets:manifest.assets}));
}finally{esbuild.stop();}
