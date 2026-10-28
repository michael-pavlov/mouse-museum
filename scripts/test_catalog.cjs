// Execute the real catalogue script with a small DOM adapter.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const locationKey=d=>{const explicit=d.whereToSee;if(explicit!==undefined){const key=(typeof explicit==='string'?explicit:(explicit.ru||explicit.en))||'unknown';return key.toLowerCase()==='local'?'local':key;}return d.sourceProperties?.['Где посмотреть']||'unknown';};
const items = fs.readdirSync(path.join(root, 'content/mice')).filter(f=>f.endsWith('.json')).map(f => JSON.parse(fs.readFileSync(path.join(root, 'content/mice', f)))).sort((a,b) => a.order-b.order);
function setup(search='', lang='en') {
 const make = () => ({children:[],attrs:{},options:[],value:'',checked:false,addEventListener(e,fn){this[e]=fn;},setAttribute(k,v){this.attrs[k]=v;},append(c){const i=this.children.indexOf(c);if(i>=0)this.children.splice(i,1);this.children.push(c);},after(c){this.afterNode=c;},replaceChildren(){this.children=[];},scrollIntoView(){}});
 const els={};
 for(const id of ['q','brand','year','tracking','interface','location','soviet','sort','catalog','count','empty'])els['#'+id]=make();
 for(const key of ['brand','year','tracking','interface','location'])els['#'+key].options=[{value:''},...items.map(d=>({value:String(key==='tracking'?d.tracking.key:key==='location'?locationKey(d):key==='year'&&d.year===null?'unknown':d[key])}))];
 els['#year'].options.push({value:'unknown'});
 els['#sort'].value='oldest';els['#sort'].options=['curated','name','oldest','newest','published-newest','published-oldest'].map(value=>({value}));els['#soviet'].type='checkbox';
 els['.filter-toggle']=make();els['.toolbar']=make();els['[data-language]']=make();const reset=make();
 const cards=items.map(d=>({dataset:{published:String(Number(d.source.replace(/\/$/,'').split('/').pop())),order:String(d.order),title:d.title[lang],year:d.year===null?'unknown':String(d.year),brand:d.brand,location:locationKey(d),tracking:d.tracking.key,interface:d.interface||'unknown',soviet:String(d.soviet),search:d.title[lang].toLowerCase()}}));
 els['#catalog'].children=[...cards];
 const document={documentElement:{lang},createElement:make,querySelector:s=>els[s]||null,querySelectorAll:s=>s==='#catalog .card'?[...els['#catalog'].children]:s==='[data-reset]'?[reset]:[]};
 let url, onIntersect;
 const saved=new Map();
 class Observer{constructor(fn){onIntersect=fn;}observe(){}disconnect(){}}
 vm.runInNewContext(fs.readFileSync(path.join(root,'assets/app.js'),'utf8'),{sessionStorage:{setItem:(k,v)=>saved.set(k,v)},IntersectionObserver:Observer,document,location:{search,href:'http://localhost/'+lang+'/'+search},URL,URLSearchParams,history:{replaceState(a,b,u){url=u;}}});
 return {saved,els,cards,reset,intersect:()=>onIntersect([{isIntersecting:true}]),visible:()=>cards.filter(c=>!c.hidden),pages:()=>els['#catalog'].afterNode,url:()=>url};
}
for(const lang of ['en','ru']){
 const s=setup('',lang);assert.equal(s.visible().length,30);
 assert.equal(s.pages().hidden,false);
 s.intersect();
 assert.equal(s.url().searchParams.get('page'),'2');assert.equal(s.visible().length,Math.min(items.length,60));
 const oldest=[...items].sort((a,b)=>(a.year===null)-(b.year===null)||(a.year-b.year)||a.order-b.order);
 assert.deepEqual(s.els['#catalog'].children.filter(c=>!c.hidden).map(c=>c.dataset.title),oldest.slice(0,60).map(d=>d.title[lang]));
 while(!s.pages().hidden)s.intersect();assert.equal(s.visible().length,items.length);
 for(const mode of ['oldest','newest','name','curated','published-newest','published-oldest']){
  s.els['#sort'].value=mode;s.els['#sort'].change();assert.equal(s.url().searchParams.has('page'),false);
  let expected=[...items].sort((a,b)=>(mode==='published-newest'?Number(b.source.replace(/\/$/,'').split('/').pop())-Number(a.source.replace(/\/$/,'').split('/').pop()):mode==='published-oldest'?Number(a.source.replace(/\/$/,'').split('/').pop())-Number(b.source.replace(/\/$/,'').split('/').pop()):mode==='oldest'?a.year-b.year:mode==='newest'?b.year-a.year:mode==='name'?a.title[lang].localeCompare(b.title[lang]):0)||a.order-b.order).slice(0,30);
  if(mode==='oldest'||mode==='newest')expected=[...items.filter(d=>d.year!==null).sort((a,b)=>(mode==='oldest'?a.year-b.year:b.year-a.year)||a.order-b.order),...items.filter(d=>d.year===null)].slice(0,30);
  const rendered=s.els['#catalog'].children.filter(c=>!c.hidden);
  assert.deepEqual(rendered.map(c=>c.dataset.title),expected.map(d=>d.title[lang]));
 }
 s.els['#soviet'].checked=true;s.els['#soviet'].change();assert.equal(s.visible().length,Math.min(30,items.filter(d=>d.soviet).length));assert(s.visible().every(c=>c.dataset.soviet==='true'));
 s.els['#soviet'].checked=false;s.els['#soviet'].change();assert.equal(s.visible().length,30);
 s.els['#location'].value='Краснохолмская';s.els['#location'].change();assert.equal(s.visible().length,Math.min(30,items.filter(d=>locationKey(d)==='Краснохолмская').length));assert(s.visible().every(c=>c.dataset.location==='Краснохолмская'));
 assert.equal(s.url().searchParams.get('location'),'Краснохолмская');assert.equal(s.saved.get('mouse-museum:catalogue:'+lang),s.url().href);assert.equal(s.els['[data-language]'].search,s.url().search);
 const direct=setup('?location='+encodeURIComponent('Краснохолмская'),lang);assert.equal(direct.visible().length,s.visible().length);
 s.els['#brand'].value='Microsoft';s.els['#brand'].change();assert(s.visible().every(c=>c.dataset.brand==='Microsoft'&&c.dataset.location==='Краснохолмская'));
 s.reset.click();
 s.els['#year'].value='1983';s.els['#year'].change();assert(s.visible().every(c=>c.dataset.year==='1983'));
 assert.equal(s.els['[data-language]'].search,s.url().search);
 s.els['#q'].value='no-such-specimen';s.els['#q'].input();assert.equal(s.visible().length,0);assert.equal(s.els['#empty'].hidden,false);assert.equal(s.pages().hidden,true);
 s.reset.click();assert.equal(s.visible().length,30);assert.equal(s.els['#sort'].value,'oldest');assert.equal(s.url().searchParams.has('sort'),false);
 s.pages().children[0].click();assert.equal(s.visible().length,Math.min(items.length,60));
 const unmarked=setup('?year=unknown',lang);assert.equal(unmarked.visible().length,Math.min(30,items.filter(d=>d.year===null).length));
 const last=setup('?page=999',lang);assert.equal(last.url().searchParams.get('page'),String(Math.ceil(items.length/30)));assert.equal(last.visible().length,items.length);
}
// A missing year must remain filterable and sort after dated objects in either direction.
const originalYear=items[0].year,previouslyUnmarked=items.filter(d=>d.year===null).length;
items[0].year=null;
for(const mode of ['oldest','newest']){
 const s=setup('?sort='+mode);
 while(!s.pages().hidden)s.intersect();
 assert.equal(s.els['#catalog'].children.at(-1).dataset.year,'unknown');
}
assert.equal(setup('?year=unknown').visible().length,Math.min(30,previouslyUnmarked+1));
items[0].year=originalYear;
console.log('OK: EN/RU infinite scroll, load-more button, URL state, six sorting modes, exact year, empty results and reset.');

// Specimen breadcrumb restores the exact query; unrelated/stale origins are rejected.
for(const lang of ['en','ru']){
 for(const stored of ['http://localhost/'+lang+'/index.html?brand=Microsoft&sort=newest&page=2','https://other.example/'+lang+'/index.html?brand=Microsoft',null]){
  const back={href:'http://localhost/'+lang+'/index.html'};
  const document={documentElement:{lang},querySelector:s=>s==='.breadcrumb a'?back:null,querySelectorAll:()=>[]};
  vm.runInNewContext(fs.readFileSync(path.join(root,'assets/app.js'),'utf8'),{document,URL,location:{href:'http://localhost/'+lang+'/mice/example/'},sessionStorage:{getItem:key=>{assert.equal(key,'mouse-museum:catalogue:'+lang);return stored;}}});
  assert.equal(back.href,stored?.startsWith('http://localhost/')?stored:'http://localhost/'+lang+'/index.html');
 }
}
console.log('OK: catalogue return state and breadcrumb in both languages.');
