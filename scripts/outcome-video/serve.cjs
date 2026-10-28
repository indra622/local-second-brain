// Loopback-only static QA server with byte ranges for native video seeking.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const root=process.cwd();const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.mp4':'video/mp4','.vtt':'text/vtt','.jpg':'image/jpeg','.png':'image/png','.txt':'text/plain','.gif':'image/gif'};
const server=http.createServer((req,res)=>{
 let file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
 if(!file.startsWith(root+path.sep)&&file!==root){res.writeHead(403).end();return;}
 try{if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');const size=fs.statSync(file).size;const headers={'Content-Type':types[path.extname(file)]||'application/octet-stream','Accept-Ranges':'bytes'};const match=/^bytes=(\d+)-(\d*)$/.exec(req.headers.range||'');let start=0,end=size-1;if(match){start=Number(match[1]);end=match[2]?Math.min(Number(match[2]),end):end;if(start>end){res.writeHead(416,{'Content-Range':`bytes */${size}`}).end();return;}headers['Content-Range']=`bytes ${start}-${end}/${size}`;}headers['Content-Length']=end-start+1;res.writeHead(match?206:200,headers);if(req.method==='HEAD')res.end();else fs.createReadStream(file,{start,end}).pipe(res);}catch{res.writeHead(404).end('Not found');}
});
server.listen(Number(process.env.PORT||8938),'127.0.0.1',()=>console.log('Owned loopback QA server ready'));
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>server.close(()=>process.exit(0)));
