(()=>{'use strict';const ru=document.documentElement.lang==='ru';const t=(en,r)=>ru?r:en;const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
const metrikaId=113889111;function goal(name){try{if(typeof ym==='function')ym(metrikaId,'reachGoal',name);}catch(e){}}
// Keep the catalogue return destination within this browser tab.
const catalogueStateKey='mouse-museum:catalogue:'+document.documentElement.lang;
const catalogueBack=$('.breadcrumb a');
if(catalogueBack){
 try{
  const saved=sessionStorage.getItem(catalogueStateKey);
  if(saved){
   const previous=new URL(saved,location.href),target=new URL(catalogueBack.href,location.href);
   // Only reuse state for a local catalogue, including sites hosted in a subfolder.
   if(previous.origin===target.origin&&(previous.pathname===target.pathname||previous.pathname===target.pathname.replace(/(?:en|ru)\/index\.html$/,'index.html'))){target.search=previous.search;catalogueBack.href=target.href;}
  }
 }catch{} // Storage can be unavailable for locally opened files.
}
// Custom filter menus are anchored below their trigger; selects retain state.
const filterMenus=[];
$$('.filter-field select').forEach(select=>{
 const field=select.parentElement;
 const trigger=document.createElement('button');trigger.type='button';trigger.className='filter-trigger';
 const menu=document.createElement('div');menu.className='filter-menu';menu.id=select.id+'-menu';menu.hidden=true;menu.setAttribute('role','listbox');menu.setAttribute('aria-label',select.getAttribute('aria-label'));
 trigger.setAttribute('aria-haspopup','listbox');trigger.setAttribute('aria-expanded','false');trigger.setAttribute('aria-controls',menu.id);
 const options=[...select.options].map(option=>{const button=document.createElement('button');button.type='button';button.className='filter-option';button.textContent=option.textContent;button.setAttribute('role','option');button.tabIndex=-1;button.addEventListener('click',()=>{select.value=option.value;select.dispatchEvent(new Event('change',{bubbles:true}));close();trigger.focus();});menu.append(button);return button;});
 function sync(){trigger.textContent=select.selectedOptions[0]?.textContent||select.options[0].textContent;trigger.setAttribute('aria-label',select.getAttribute('aria-label')+': '+trigger.textContent);options.forEach((button,i)=>button.setAttribute('aria-selected',String(i===select.selectedIndex)));}
 function close(){menu.hidden=true;trigger.setAttribute('aria-expanded','false');}
 function open(){filterMenus.forEach(m=>m.close());menu.hidden=false;trigger.setAttribute('aria-expanded','true');options[Math.max(0,select.selectedIndex)].focus();}
 trigger.addEventListener('click',()=>menu.hidden?open():close());
 trigger.addEventListener('keydown',e=>{if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();open();}});
 menu.addEventListener('keydown',e=>{let i=options.indexOf(document.activeElement);if(e.key==='Escape'){e.preventDefault();close();trigger.focus();}else if(e.key==='Tab'){close();}else if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();i=e.key==='Home'?0:e.key==='End'?options.length-1:(i+(e.key==='ArrowDown'?1:-1)+options.length)%options.length;options[i].focus();}});
 select.hidden=true;field.append(trigger,menu);select.addEventListener('change',sync);sync();filterMenus.push({field,close,sync});
});
if(filterMenus.length)document.addEventListener('click',e=>filterMenus.forEach(m=>{if(!m.field.contains(e.target))m.close();}));

function compareYears(a,b,newest=false){
 const x=Number(a.dataset.year),y=Number(b.dataset.year),knownX=Number.isFinite(x),knownY=Number.isFinite(y);
 if(!knownX||!knownY)return knownX?-1:knownY?1:0;
 return newest?y-x:x-y;
}
const cards=$$('#catalog .card');
if($('#catalog')){
 const ids=['q','brand','year','tracking','interface','location','soviet','sort'];
 const pageSize=30;
 const initial=new URLSearchParams(location.search);
 let page=Math.max(1,Number(initial.get('page'))||1);
 ids.forEach(id=>{const el=$('#'+id);if(initial.has(id)){if(el.type==='checkbox')el.checked=initial.get(id)==='1';else if(id==='q'||[...el.options].some(o=>o.value===initial.get(id)))el.value=initial.get(id);}});
 const more=document.createElement('div');more.className='load-more';
 const loadButton=document.createElement('button');loadButton.type='button';loadButton.className='button';loadButton.textContent=t('Show more','Показать ещё');more.append(loadButton);$('#catalog').after(more);
 function loadMore(){if(more.hidden)return;page++;filter();}
 loadButton.addEventListener('click',loadMore);
 const observer=typeof IntersectionObserver==='undefined'?null:new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting))loadMore();},{rootMargin:'0px 0px 200px 0px'});

 function filter(){
  filterMenus.forEach(m=>m.sync());
  const q=$('#q').value.trim().toLocaleLowerCase(),sort=$('#sort').value;
  cards.sort((a,b)=>(sort==='name'?a.dataset.title.localeCompare(b.dataset.title):sort==='published-newest'?+b.dataset.published-+a.dataset.published:sort==='published-oldest'?+a.dataset.published-+b.dataset.published:sort==='newest'?compareYears(a,b,true):sort==='oldest'?compareYears(a,b):0)||+a.dataset.order-+b.dataset.order);
  const matches=cards.filter(card=>(!q||q.split(/\s+/).every(word=>card.dataset.search.includes(word)))&&['brand','year','tracking','interface','location'].every(key=>!$('#'+key).value||card.dataset[key]===$('#'+key).value)&&(!$('#soviet').checked||card.dataset.soviet==='true'));
  const pages=Math.max(1,Math.ceil(matches.length/pageSize));page=Math.min(pages,Math.max(1,Math.floor(page)));
  const visible=new Set(matches.slice(0,page*pageSize));cards.forEach(card=>{card.hidden=!visible.has(card);});
  const rendered=$$('#catalog .card');if(cards.some((card,i)=>rendered[i]!==card))cards.forEach(card=>$('#catalog').append(card));
  $('#count').textContent=t(`Showing ${visible.size} of ${matches.length} objects.`,`Показано ${visible.size} из ${matches.length} экспонатов.`);$('#empty').hidden=matches.length>0;
  const url=new URL(location.href);
  ids.forEach(id=>{const el=$('#'+id),value=el.type==='checkbox'?(el.checked?'1':''):el.value;if(value&&!(id==='sort'&&value==='oldest'))url.searchParams.set(id,value);else url.searchParams.delete(id)});
  if(page>1)url.searchParams.set('page',page);else url.searchParams.delete('page');
  try{history.replaceState(null,'',url)}catch{}
  try{sessionStorage.setItem(catalogueStateKey,url.href)}catch{}
  const lang=$('[data-language]');if(lang)lang.search=url.search;
  more.hidden=page>=pages;
  if(observer){observer.disconnect();if(!more.hidden)observer.observe(more);}

 }
 ids.forEach(id=>$('#'+id).addEventListener(id==='q'?'input':'change',()=>{page=1;filter()}));
 function reset(){ids.forEach(id=>{const el=$('#'+id);if(el.type==='checkbox')el.checked=false;else el.value=id==='sort'?'oldest':''});page=1;filter()}
 $$('[data-reset]').forEach(b=>b.addEventListener('click',reset));$('.filter-toggle').addEventListener('click',e=>{const open=$('.filters').classList.toggle('open');e.currentTarget.setAttribute('aria-expanded',String(open))});filter();
}

const thumbs=$$('.thumbs button');let current=0;function photo(n){current=(n+thumbs.length)%thumbs.length;const thumb=thumbs[current];$('#main-image').src=thumb.dataset.src;$('#main-image').alt=thumb.dataset.alt;$('#photo-count').textContent=`${String(current+1).padStart(2,'0')} / ${String(thumbs.length).padStart(2,'0')}`;thumbs.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===current)));if($('#lightbox-image')&&$('#lightbox').open){$('#lightbox-image').src=thumb.dataset.src;$('#lightbox-image').alt=thumb.dataset.alt}}if(thumbs.length){thumbs.forEach((b,i)=>b.addEventListener('click',()=>photo(i)));$$('[data-step]').forEach(b=>b.addEventListener('click',()=>photo(current+Number(b.dataset.step))));$('.zoom').addEventListener('click',()=>{$('#lightbox').showModal();photo(current);document.documentElement.classList.add('photo-viewer-open');goal('photo_zoom')});$('#lightbox').addEventListener('close',()=>document.documentElement.classList.remove('photo-viewer-open'));document.addEventListener('keydown',e=>{if($('#lightbox').open){if(e.key==='ArrowRight'){e.preventDefault();photo(current+1)}if(e.key==='ArrowLeft'){e.preventDefault();photo(current-1)}}})}
$$('[data-close]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));$$('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close()}}));
const permalink=()=>location.href.split('#')[0].split('?')[0];async function copy(value){try{await navigator.clipboard.writeText(value);return true}catch{return false}}function renderShare(){const type=$('[data-share-format][aria-pressed="true"]').dataset.shareFormat,url=permalink(),title=$('h1').textContent,img=new URL($('#main-image').getAttribute('src'),location.href).href;$('#share-text').value=type==='bbcode'?`[url=${url}]${title}[/url]`:type==='markdown'?`[${title}](${url})`:type==='image'?`[url=${url}][img]${img}[/img][/url]`:url;$('#share-status').textContent='';resizeShareField()}function resizeShareField(){const field=$('#share-text'),value=field.value,url=permalink(),img=new URL($('#main-image').getAttribute('src'),location.href).href;field.style.height='auto';const variants=[value,url,`[url=${url}]${$('h1').textContent}[/url]`,`[${$('h1').textContent}](${url})`,`[url=${url}][img]${img}[/img][/url]`];let height=0;for(const variant of variants){field.value=variant;height=Math.max(height,field.scrollHeight)}field.value=value;field.style.height=height+'px'}if($('#forum-link')){$('#forum-link').addEventListener('click',()=>{renderShare();$('#share').showModal();resizeShareField()});window.addEventListener('resize',()=>{if($('#share').open)resizeShareField()});$$('[data-share-format]').forEach(button=>button.addEventListener('click',()=>{$$('[data-share-format]').forEach(option=>option.setAttribute('aria-pressed',String(option===button)));renderShare()}));$('#copy-share').addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();$('#copy-share').click()}});$('#copy-share').addEventListener('click',async()=>{if(await copy($('#share-text').value)){$('#share-status').textContent=t('Copied. Ready to paste.','Скопировано. Можно вставлять.');goal('copy_share')}else{$('#share-text').focus();$('#share-text').select();$('#share-status').textContent=t('Press Ctrl+C or ⌘C to copy.','Нажмите Ctrl+C или ⌘C.')}})}

// Image links stay on the current page, with a native modal and explicit close.
const imageLinks=$$('a.wanted-photo, a.article-photo');
if(imageLinks.length){
 const viewer=document.createElement('dialog');viewer.className='photo-viewer';viewer.setAttribute('aria-label',t('Photograph viewer','Просмотр фотографии'));
 if(typeof viewer.showModal==='function'){
  const head=document.createElement('div');head.className='photo-viewer-head';
  const caption=document.createElement('span');
  const close=document.createElement('button');close.type='button';close.className='photo-viewer-close';close.textContent='×';close.setAttribute('aria-label',t('Close photograph','Закрыть фотографию'));close.autofocus=true;
  const image=document.createElement('img');image.className='photo-viewer-image';
  head.append(caption,close);viewer.append(head,image);document.body.append(viewer);
  let opener=null;
  imageLinks.forEach(link=>link.addEventListener('click',e=>{
   if(e.button||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
   e.preventDefault();opener=link;
   const thumbnail=link.querySelector('img');image.alt=thumbnail?.alt||t('Photograph','Фотография');caption.textContent=image.alt;image.src=link.href;
   viewer.showModal();document.documentElement.classList.add('photo-viewer-open');goal('photo_zoom');
  }));
  close.addEventListener('click',()=>viewer.close());
  viewer.addEventListener('click',e=>{if(e.target!==viewer)return;const rect=viewer.getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)viewer.close();});
  viewer.addEventListener('close',()=>{document.documentElement.classList.remove('photo-viewer-open');image.removeAttribute('src');opener?.focus({preventScroll:true});});
 }
}
function emailGoal(link){
 const path=location.pathname||'';
 if(link.classList.contains('about-email'))return 'email_about';
 if(link.classList.contains('exchange-propose')||link.closest('.exchange-card')||path.includes('/wanted/exchange/'))return 'email_exchange';
 if(link.classList.contains('wanted-offer')||path.includes('/wanted/'))return 'email_wanted';
 return '';
}
$$('a[href^="mailto:"]').forEach(link=>link.addEventListener('click',()=>{const name=emailGoal(link);if(name)goal(name);}));
})();
