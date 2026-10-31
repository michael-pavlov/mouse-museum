const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(require('node:path').join(__dirname,'../assets/app.js'),'utf8');
const goals=[];
function setup(supported=true){
 goals.length=0;
 const classes=new Set();
 const node=()=>({children:[],attrs:{},events:{},addEventListener(name,fn){this.events[name]=fn;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this[k];},append(...nodes){this.children.push(...nodes);},focus(options){this.focused=options;}});
 const link=node();link.href='http://localhost/assets/wanted/example/photo.webp';link.querySelector=()=>({alt:'Wanted mouse W-01'});
 const body=node();let dialog;
 const document={documentElement:{lang:'ru',classList:{add(c){classes.add(c);},remove(c){classes.delete(c);}}},body,
 querySelector(){return null;},querySelectorAll(s){return s==='a.wanted-photo, a.article-photo'?[link]:[];},
 createElement(tag){const el=node();if(tag==='dialog'){dialog=el;el.getBoundingClientRect=()=>({left:10,right:100,top:10,bottom:100});if(supported){el.showModal=()=>{el.open=true;};el.close=()=>{el.open=false;el.events.close();};}}return el;}};
 vm.runInNewContext(source,{document,ym:(id,method,name)=>goals.push([id,method,name])});
 return {link,body,dialog,classes};
}
const s=setup();let prevented=false;
s.link.events.click({button:0,preventDefault(){prevented=true;}});
assert(prevented);assert(s.dialog.open);assert(s.classes.has('photo-viewer-open'));
assert.equal(s.dialog.children[1].src,s.link.href);
assert.equal(s.dialog.children[1].alt,'Wanted mouse W-01');
s.dialog.events.click({target:s.dialog,clientX:50,clientY:50});assert(s.dialog.open);
s.dialog.events.click({target:s.dialog,clientX:0,clientY:0});assert.equal(s.dialog.open,false);assert(!s.classes.has('photo-viewer-open'));assert.equal(s.link.focused.preventScroll,true);
s.link.events.click({button:0,preventDefault(){}});s.dialog.children[0].children[1].events.click();assert.equal(s.dialog.open,false);
prevented=false;s.link.events.click({button:0,metaKey:true,preventDefault(){prevented=true;}});assert.equal(prevented,false);assert.equal(s.dialog.open,false);
assert.deepEqual(goals.filter(goal=>goal[2]==='photo_zoom'),[[113889111,'reachGoal','photo_zoom'],[113889111,'reachGoal','photo_zoom']]);
assert.equal(setup(false).link.events.click,undefined);
console.log('OK: photo overlay, close button, backdrop, scroll unlock, focus return and link fallback.');
