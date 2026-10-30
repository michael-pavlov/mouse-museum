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
 const elements={
  '#copy-link':el(),
  '#forum-link':el(),
  '#copy-status':{textContent:''},
  '#copy-share':el(),
  '#share-format':el(),
  '#share-status':{textContent:''},
  '#share-text':{value:'forum text'},
 };
 const document={
  documentElement:{lang:'en'},
  querySelector:selector=>elements[selector]||null,
  querySelectorAll:selector=>selector==='a[href^="mailto:"]'?mailtos:[],
 };
 const navigator={clipboard:{async writeText(){return true;}}};
 vm.runInNewContext(source,{document,navigator,location:{href:'https://mouse.museum'+pathname,pathname},ym:(id,method,name)=>goals.push([id,method,name])});
 return {goals,elements};
}

(async()=>{
 const wanted=el('button wanted-offer');
 const exchangeCard=el('button wanted-offer');exchangeCard.exchangeCard={};
 const propose=el('button exchange-propose');
 const about=el('about-email');
 const footer=el();

 const wantedPage=boot('/ru/wanted/index.html',[wanted,footer]);
 await wantedPage.elements['#copy-link'].events.click();
 wanted.events.click();
 footer.events.click();
 assert.deepEqual(wantedPage.goals,[
  [113889111,'reachGoal','copy_share'],
  [113889111,'reachGoal','email_wanted'],
  [113889111,'reachGoal','email_wanted'],
 ]);

 const exchangePage=boot('/en/wanted/exchange/index.html',[exchangeCard,propose,footer]);
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
