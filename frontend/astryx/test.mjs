import test from 'node:test';
import assert from 'node:assert/strict';
import {overview,eligible,classicDestination} from './src/selectors.mjs';
const path=id=>`concepts/${id}/r000001.md`;
const good={metadata_errors:[],status:'stable',stale:null,verified:null,title:'현재 생각',body:'public synthetic'};
const snapshot={current:{constructor:path('constructor'),missing:path('missing'),overdue:path('overdue')},notes:{[path('constructor')]:good,[path('overdue')]:{...good,stale:true,verified:[{by:'process:synthetic'}]},'concepts/constructor/r000002.md':{...good}},sources:{}};
test('actual current vs revision, unknown and review declaration counts',()=>assert.deepEqual(overview(snapshot),{current:3,revisions:3,unread:1,overdue:1,unknown:2,reviews:1}));
test('constructor remains legal; destinations contain only validated loaded revisions',()=>{
 assert.equal(classicDestination(snapshot,'constructor','sources'),'../#note=constructor&revision=r000001&panel=sources');
 for(const [id,panel] of [['../outside','body'],['constructor','https://evil.test'],['missing','body'],['absent','body']])assert.equal(classicDestination(snapshot,id,panel),null);
});
test('search/topic eligibility recomputes on refreshed snapshot without stale detail',()=>{
 const graph={nodes:new Map([['constructor',{note:good,topic:'기록'}],['missing',{note:null,topic:null}]])};
 assert.deepEqual(eligible(snapshot,graph,'생각',JSON.stringify('기록')),['constructor']);
 graph.nodes.set('constructor',{note:{...good,title:'다른 제목',body:'changed'},topic:'기록'});
 assert.deepEqual(eligible(snapshot,graph,'생각',JSON.stringify('기록')),[]);
 assert.deepEqual(eligible(snapshot,graph,'',JSON.stringify(null)),['missing']);
});
