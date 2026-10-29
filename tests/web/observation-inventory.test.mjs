import {test} from 'node:test';
import assert from 'node:assert/strict';
import {observationInventory} from '../../web/observation-inventory.js';
const protocol={outcomes:[{id:'o1'}],factors:[{key:'factor_design',label:'Study design'}]};
const project={papers:[{id:'paper',title:'Source paper',metrics:[
 {id:'a',name:'Outcome A',value:'1',protocol,outcomeId:'o1',quote:'Source A',missing:['factor_design']},
 {id:'b',name:'Outcome B',value:'2',protocol,outcomeId:'outside_scope',quote:'Source B'},
 {id:'c',name:'Outcome A',value:'3',protocol,outcomeId:'unknown',quote:'Source C'}]}]};
const side=metric=>({paper:'paper',metric,method:'Method '+metric,name:'Outcome',value:'1'});
test('all observations survive scope filtering of comparison candidates',()=>{
 const x=observationInventory(project,[]);
 assert.equal(x.total,3);assert.equal(x.labels,2);
 assert.equal(x.assigned,1);assert.equal(x.outside,1);assert.equal(x.unresolved,1);
 assert.equal(x.rows[1].quote,'Source B');assert.deepEqual(x.rows[0].missing,['Study design']);
});
test('pending pairs are never counted as incompatible or insufficient findings',()=>{
 const x=observationInventory(project,[{a:side('a'),b:side('c'),assessed:false,outcome:'insufficient'}]);
 assert.equal(x.rows[0].comparisons.pending,1);assert.equal(x.rows[0].comparisons.insufficient,0);
 assert.deepEqual(x.rows[0].assessments,[]);
});
test('one observation can participate in different pair outcomes with recorded reasons',()=>{
 const x=observationInventory(project,[{id:'p1',a:side('a'),b:side('b'),assessed:true,outcome:'incompatible',explanation:['Different populations']},{id:'p2',a:side('a'),b:side('c'),assessed:true,outcome:'comparable',explanation:['Conditions aligned']}]);
 assert.equal(x.rows[0].comparisons.incompatible,1);assert.equal(x.rows[0].comparisons.comparable,1);
 assert.equal(x.rows[0].assessments[0].reasons[0],'Different populations');
 assert.equal(x.rows[0].scope,'assigned');
});
