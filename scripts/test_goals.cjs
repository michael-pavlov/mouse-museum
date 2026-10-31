const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../assets/app.js'),'utf8');

function el(className=''){
 const classes=new Set(className.split(/\s+/).filter(Boolean));
 const node={
  classList:{contains:name=>classes.has(name)},
  events:{},
  addEventListener(name,fn){this.events[name]=fn;},
  closest(selector){return selector==='.exchange-card'?this.exchangeCard:null;},
  href:'mailto:mr.michael.pavlov@gmail.com',
 };
 return node;
}

function boot(pathname, mailtos){
 const goals=[];
 const formats=['url','bbcode','markdown','image'].map(format=>({
  ...el(),dataset:{shareFormat:format},pressed:format==='url',
  setAttribute(name,value){if(name==='aria-pressed')this.pressed=value==='true';},
 }));
 const elements={
  '#forum-link':el(),
  '#copy-status':{textContent:''},
  '#copy-share':el(),
  '#share-format':el(),
  '#share-status':{textContent:''},
  '#share-text':{value:'forum text',style:{},scrollHeight:90},
  '#share':{open:false,showModal(){this.open=true;}},
  'h1':{textContent:'Test specimen'},
  '#main-image':{getAttribute(){return '/assets/example.webp';}},
 };
 const document={
  documentElement:{lang:'en'},
  querySelector:selector=>selector==='[data-share-format][aria-pressed="true"]'?formats.find(x=>x.pressed):elements[selector]||null,
  querySelectorAll:selector=>selector==='a[href^="mailto:"]'?mailtos:selector==='[data-share-format]'?formats:[],
 };
 const navigator={clipboard:{async writeText(){return true;}}};
 vm.runInNewContext(source,{document,navigator,URL,window:{addEventListener(){}},location:{href:'https://mouse.museum'+pathname,pathname},ym:(id,method,name)=>goals.push([id,method,name])});
 return {goals,elements,formats};
}

(async()=>{
 const wanted=el('button wanted-offer');
 const exchangeCard=el('button wanted-offer');exchangeCard.exchangeCard={};
 const propose=el('button exchange-propose');
 const about=el('about-email');
 const footer=el();

 const wantedPage=boot('/ru/wanted/index.html',[wanted,footer]);
 wantedPage.elements['#forum-link'].events.click();
 assert(wantedPage.elements['#share'].open);
 assert.equal(wantedPage.elements['#share-text'].value,'https://mouse.museum/ru/wanted/index.html');
 await wantedPage.elements['#copy-share'].events.click();
 wanted.events.click();
 footer.events.click();
 assert.deepEqual(wantedPage.goals,[
  [113889111,'reachGoal','copy_share'],
  [113889111,'reachGoal','email_wanted'],
  [113889111,'reachGoal','email_wanted'],
 ]);

 const exchangePage=boot('/en/wanted/exchange/index.html',[exchangeCard,propose,footer]);
 exchangePage.formats[1].events.click();
 assert.equal(exchangePage.elements['#share-text'].value,'[url=https://mouse.museum/en/wanted/exchange/index.html]Test specimen[/url]');
 await exchangePage.elements['#copy-share'].events.click();
 exchangeCard.events.click();
 propose.events.click();
 footer.events.click();
 assert.deepEqual(exchangePage.goals,[
  [113889111,'reachGoal','copy_share'],
  [113889111,'reachGoal','email_exchange'],
  [113889111,'reachGoal','email_exchange'],
  [113889111,'reachGoal','email_exchange'],
 ]);

 const aboutPage=boot('/en/about/index.html',[about]);
 about.events.click();
 assert.deepEqual(aboutPage.goals,[[113889111,'reachGoal','email_about']]);
 console.log('OK: copy, wanted, exchange and about goals.');
})().catch(error=>{console.error(error);process.exit(1);});
