export const owns=(object,key)=>Object.prototype.hasOwnProperty.call(object,key);
export function overview(snapshot){
  const current=Object.values(snapshot.current).map(path=>snapshot.notes[path]);
  const good=n=>n&&Array.isArray(n.metadata_errors)&&!n.metadata_errors.length;
  return {current:current.length,revisions:Object.keys(snapshot.notes).length,unread:current.filter(n=>!n).length,
    overdue:current.filter(n=>good(n)&&n.stale===true).length,
    unknown:current.filter(n=>!good(n)||n.stale===null).length,
    reviews:current.filter(n=>good(n)&&n.verified&&(!Array.isArray(n.verified)||n.verified.length)).length};
}
export function eligible(snapshot,graph,query,topic){
  const text=query.trim().toLocaleLowerCase();
  return [...graph.nodes.keys()].filter(id=>{
    const n=graph.nodes.get(id).note;
    return (!text||((typeof n?.title==='string'?n.title:id)+'\n'+(n?.body||'')).toLocaleLowerCase().includes(text))
      &&(!topic||JSON.stringify(graph.nodes.get(id).topic)===topic);
  });
}
export function classicDestination(snapshot,id,panel){
  if(!/^[a-z0-9][a-z0-9-]{0,63}$/.test(id)||!owns(snapshot.current,id)||!['body','sources','history','related'].includes(panel))return null;
  const path=snapshot.current[id],match=typeof path==='string'&&path.match(new RegExp('^concepts/'+id+'/(r[0-9]{6})\\.md$'));
  if(!match||match[1]==='r000000'||!owns(snapshot.notes,path))return null;
  return '../#'+new URLSearchParams({note:id,revision:match[1],panel}).toString();
}
