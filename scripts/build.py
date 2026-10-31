#!/usr/bin/env python3
"""Build a bilingual static museum catalogue. Python 3.11+ with Python-Markdown for journal articles."""
import argparse,hashlib,html,json,os,posixpath,re,shutil
from pathlib import Path
from urllib.parse import urlparse,urlencode
from journal import Journal
from wanted import Wanted
from specimen_content import validate_extras, viewing_location, viewing_location_key, description_html, resources_html
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
parser=argparse.ArgumentParser();parser.add_argument('--site-url',default=os.environ.get('SITE_URL',''));args=parser.parse_args()
SITE=args.site_url.rstrip('/')
if SITE and (urlparse(SITE).scheme not in ('https','http') or not urlparse(SITE).netloc):raise SystemExit('SITE_URL must be an absolute http(s) URL')
items=sorted([json.loads(p.read_text()) for p in (ROOT/'content/mice').glob('*.json')],key=lambda d:d['order'])
assert items,'No catalogue entries'
def publication_id(d):return int(d['source'].rstrip('/').rsplit('/',1)[-1])
newest_ids={d['id'] for d in sorted(items,key=publication_id,reverse=True)[:4]}
seen=set()
for d in items:
 validate_extras(d)
 assert re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',d['slug']),d['slug']
 assert d['slug'] not in seen,'Duplicate slug';seen.add(d['slug'])
 for language in ('en','ru'):assert d['title'][language] and d['manufacturer'][language]
 assert d['photos'],'Every object needs a photo'
 for p in [d['thumbnail']]+[value for photo in d['photos'] for key in ('file','thumbnail') if (value:=photo.get(key))]:
  target=(ROOT/p).resolve();assert target.is_relative_to(ROOT/'assets') and target.is_file(),p
journal=Journal(ROOT,items)
wanted=Wanted(ROOT,items,SITE)
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir();shutil.copytree(ROOT/'assets',OUT/'assets',ignore=shutil.ignore_patterns('originals','source-images'));(OUT/'.nojekyll').touch()
def E(v):return html.escape(str(v),quote=True)
def t(en,ru,l):return ru if l=='ru' else en
def link(path,target):return posixpath.relpath(target,posixpath.dirname(path) or '.')
def objpath(d,l):return f'{l}/mice/{d["slug"]}/index.html'
def public(path):return SITE+'/'+path.removesuffix('index.html')
icon='<svg viewBox="0 0 40 44" fill="none" aria-hidden="true"><path d="M20 1v8" stroke="currentColor" stroke-width="2"/><path d="M9 9h22l3 6v23l-3 3H9l-3-3V15l3-6Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M7 24h26M20 10v14" stroke="currentColor" stroke-width="2"/><path d="M11 14h5v6h-5zm13 0h5v6h-5z" fill="#a84728"/></svg>'
def asset(path, target):
 digest=hashlib.sha256((ROOT/target).read_bytes()).hexdigest()[:12]
 return link(path,target)+'?v='+digest
METRIKA = '''<!-- Yandex.Metrika counter -->
<script type="text/javascript">
    (function(m,e,t,r,i,k,a){
        m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
        m[i].l=1*new Date();
        for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
        k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
    })(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id=113889111', 'ym');

    ym(113889111, 'init', {ssr:true, webvisor:true, clickmap:true, ecommerce:"dataLayer", referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true});
</script>
<noscript><div><img src="https://mc.yandex.ru/watch/113889111" style="position:absolute; left:-9999px;" alt="" /></div></noscript>
<!-- /Yandex.Metrika counter -->'''
pages=[]
def shell(path,l,title,description,body,other,photo=None,*,extra_head="",body_class=""):
 alt='ru' if l=='en' else 'en';h=lambda p:link(path,p)
 meta=f'<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(description)}"><meta property="og:type" content="website"><meta property="og:locale" content="{t("en_US","ru_RU",l)}"><meta name="twitter:card" content="summary_large_image">'
 if SITE:
  meta+=f'<link rel="canonical" href="{E(public(path))}"><meta property="og:url" content="{E(public(path))}"><link rel="alternate" hreflang="{l}" href="{E(public(path))}"><link rel="alternate" hreflang="{alt}" href="{E(public(other))}">'
  if photo:
   image_url=SITE+'/'+photo
   meta+=f'<meta property="og:image" content="{E(image_url)}"><meta property="og:image:alt" content="{E(title)}"><meta name="twitter:image" content="{E(image_url)}">'
   if photo=='assets/catalogue-preview.png':meta+='<meta property="og:image:type" content="image/png"><meta property="og:image:width" content="1286"><meta property="og:image:height" content="1176">'
 content=f'''<!doctype html><html lang="{l}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} — Mouse Museum</title><meta name="description" content="{E(description)}">{meta}<link rel="stylesheet" href="{asset(path,'assets/style.css')}"><link rel="icon" href="{asset(path,'assets/favicon.svg')}" type="image/svg+xml"><link rel="icon" href="{asset(path,'assets/favicon.png')}" type="image/png" sizes="128x128"><link rel="icon" href="{asset(path,'assets/favicon.ico')}" sizes="any"><script src="{asset(path,'assets/app.js')}" defer></script>{extra_head}</head><body class="{E(body_class)}">{METRIKA}<a class="skip" href="#main">{t('Skip to content','К содержимому',l)}</a><div class="wrap"><header class="topbar"><div class="brand"><a class="brand-icon" href="{h(l+'/index.html')}" aria-label="Mouse Museum"><img src="{asset(path,'assets/mouse-museum-logo.svg')}" width="76" height="64" alt=""></a><div class="brand-copy"><a href="{h(l+'/index.html')}">Mouse Museum</a><small>THE <a class="collector-link" href="https://t.me/old_mice_and_hw">MICHAEL PAVLOV</a> COLLECTION</small></div></div><nav class="nav" aria-label="{t('Main navigation','Навигация',l)}"><a href="{h(l+'/index.html')}">{t('Catalogue','Каталог',l)} ({len(items)})</a><a href="{h(l+'/journal/index.html')}">{t('Journal','Журнал',l)}</a><a class="nav-wanted" href="{h(l+'/wanted/index.html')}">{t('Wanted','Ищется',l)}</a><a href="{h(l+'/about/index.html')}">{t('About','О музее',l)}</a><div class="lang"><a href="{h(path if l=='en' else other)}" lang="en" {'aria-current="page"' if l=='en' else 'data-language'}>EN</a><a href="{h(path if l=='ru' else other)}" lang="ru" {'aria-current="page"' if l=='ru' else 'data-language'}>RU</a></div></nav></header><main id="main">{body}</main><footer class="site-footer"><p class="footer-permission">{t('You may freely copy, share and reuse the texts and images on this site for any purpose, provided you credit Mouse Museum and link to the ','Тексты и изображения сайта можно свободно копировать, публиковать и использовать в любых целях при указании Mouse Museum и ссылки на ',l)}<a href="{h(path)}">{t('source page','страницу-источник',l)}</a>.</p></footer></div></body></html>'''
 dest=OUT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content);pages.append(path)
def card(d,l,path,i):
 h=lambda p:link(path,p);title=d['title'][l];year=d['year'];search=' '.join([*d['title'].values(),*d['manufacturer'].values(),str(year) if year is not None else '',d['interface'] or '',d['tracking']['en'],d['tracking']['ru'],d['features']['en'],d['features']['ru'],d['id']]).lower()
 attrs={'order':d['order'],'published':publication_id(d),'title':title,'year':year if year is not None else 'unknown','brand':d['brand'],'location':viewing_location_key(d),'tracking':d['tracking']['key'],'interface':d['interface'] or 'unknown','soviet':str(d['soviet']).lower(),'search':search}
 attrs=' '.join(f'data-{k}="{E(v)}"' for k,v in attrs.items())
 return f'''<a class="card" href="{h(objpath(d,l))}" title="{E(title)}" {attrs}><div class="photo"><img src="{h(d['thumbnail'])}" alt="{E(title)}" loading="{'eager' if i<3 else 'lazy'}">{t('<span class="new-badge">New</span>','<span class="new-badge">Новое</span>',l) if d['id'] in newest_ids else ''}</div><h2>{E(title)}</h2></a>'''
def catalog(l,path):
 h=lambda p:link(path,p)
 catalog_items=sorted(items,key=lambda d:(d['year'] is None,d['year'] if d['year'] is not None else 0,d['order']))
 def select(key,label,options):return f'<div class="filter-field"><span class="sr-only">{E(label)}</span><select id="{key}" aria-label="{E(label)}"><option value="">{E(label)}</option>'+''.join(f'<option value="{E(k)}">{E(v)}</option>' for k,v in options)+'</select></div>'
 brands=sorted({d['brand'] for d in items if d['brand'].lower() not in ('unknown','not recorded','не указан','не указано')});years=sorted({d['year'] for d in items if d['year'] is not None});tracks={d['tracking']['key']:d['tracking'][l] for d in items if d['tracking']['key']!='unknown'};interfaces=sorted({d['interface'] for d in items if d['interface']})
 locations={viewing_location_key(d):viewing_location(d,l) for d in items if viewing_location(d,l) and viewing_location_key(d)!='unknown'}
 filters=select('brand',t('Manufacturer','Производитель',l),[(b,b) for b in brands]+[('Unknown',t('Not recorded','Не указано',l))])+select('year',t('Year','Год',l),[(y,str(y)) for y in years]+[('unknown',t('Not recorded','Не указано',l))])+select('tracking',t('Tracking technology','Технология',l),list(tracks.items())+[('unknown',t('Not recorded','Не указано',l))])+select('interface',t('Interface / connector','Интерфейс / разъём',l),[(v,v) for v in interfaces]+[('unknown',t('Not recorded','Не указано',l))])+select('location',t('Where to see','Где посмотреть',l),sorted(locations.items(),key=lambda pair:pair[1])+[('unknown',t('Not recorded','Не указано',l))])
 body=f'''<section class="hero"><div><h1>{t('A history of clicking.','История кликов.',l)}</h1></div><div><p>{t('Exploring the history of the computer mouse, one mouse at a time. A collection of curious mechanisms, bold designs and different ways to point.','История компьютерной мыши — от модели к модели. Необычные механизмы, смелые формы и разные способы управлять курсором.',l)}</p></div></section><div class="catalog-layout"><button class="filter-toggle" aria-expanded="false" aria-controls="filters">{t('Filters','Фильтры',l)} +</button><aside class="filters" id="filters"><div class="filter-title"><button class="text-button" data-reset>{t('Reset','Сбросить',l)}</button></div>{filters}<label class="check"><input type="checkbox" id="soviet">{t('Soviet-made','Произведено в СССР',l)}</label><p class="filter-note">{t('Explore by maker, era or the mechanism inside. Each object has its own permanent page.','Ищите по производителю, эпохе или устройству механизма. У каждого экспоната есть отдельная страница.',l)}</p></aside><section aria-label="{t('Catalogue','Каталог',l)}"><div class="toolbar"><label class="search"><span class="sr-only">{t('Search the collection','Поиск по коллекции',l)}</span><svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="5.8" stroke="currentColor"/><path d="m12.5 12.5 5 5" stroke="currentColor"/></svg><input id="q" type="search" placeholder="{t('Search model, maker, year…','Модель, производитель, год…',l)}" autocomplete="off"></label><label class="sort"><span class="sr-only">{t('Sort','Сортировка',l)}</span><select id="sort"><option value="curated">{t('Collection order','Порядок коллекции',l)}</option><option value="published-newest">{t('Added: newest first','Сначала новые публикации',l)}</option><option value="published-oldest">{t('Added: oldest first','Сначала старые публикации',l)}</option><option value="oldest" selected>{t('Year: oldest first','Сначала ранние',l)}</option><option value="newest">{t('Year: newest first','Сначала поздние',l)}</option><option value="name">{t('Name: A–Z','По названию',l)}</option></select></label></div><span class="sr-only" id="count" role="status" aria-live="polite"></span><div class="grid" id="catalog">{''.join(card(d,l,path,i) for i,d in enumerate(catalog_items))}</div><div class="empty" id="empty" hidden><h2>{t('No objects found','Ничего не найдено',l)}</h2><p>{t('Try another search or remove a filter.','Попробуйте другой запрос или уберите фильтр.',l)}</p><button class="button" data-reset>{t('Reset filters','Сбросить фильтры',l)}</button></div></section></div>'''
 shell(path,l,t('Catalogue','Каталог',l),t('Computer mice, curious mechanisms and industrial design from the Michael Pavlov collection.','Компьютерные мыши, необычные механизмы и промышленный дизайн из коллекции Михаила Павлова.',l),body,('ru' if l=='en' else 'en')+'/index.html','assets/catalogue-preview.png')
def detail(d,l):
 path=objpath(d,l);h=lambda p:link(path,p);title=d['title'][l];photos=d['photos'];p0=photos[0]['file']
 fields=[(t('Manufacturer','Производитель',l),d['manufacturer'][l],'brand',d['brand']),
         (t('Year','Год',l),d['year'] if d['year'] is not None else t('Not recorded','Не указан',l),'year',d['year'] if d['year'] is not None else 'unknown'),
         (t('Tracking','Технология',l),d['tracking'][l],'tracking',d['tracking']['key']),
         (t('Interface / connector','Интерфейс / разъём',l),d['interface'] or t('Not recorded','Не указан',l),'interface',d['interface'] or 'unknown')]
 if d.get('boardManufacturer',{}).get(l):fields.append((t('Board manufacturer','Производитель платы',l),d['boardManufacturer'][l],None,None))
 if d['features'][l]:fields.append((t('Features','Особенности',l),d['features'][l],None,None))
 if d['soviet']:fields.append((t('Origin','Происхождение',l),t('Soviet Union','СССР',l),'soviet','1'))
 if viewing_location(d,l):fields.append((t('Where to see','Где посмотреть',l),viewing_location(d,l),'location',viewing_location_key(d)))
 def spec(label,value,key,filter_value):
  missing=not str(value).strip() or str(value).strip().lower() in ('unknown','not recorded','not specified','не указан','не указана','не указано') or str(filter_value).lower()=='unknown'
  content='—' if missing else E(value)
  if key and not missing:
   url=h(l+'/index.html')+'?'+urlencode({key:filter_value})
   content=f'<a class="spec-filter" href="{E(url)}">{content}</a>'
  return f'<div><dt>{E(label)}</dt><dd>{content}</dd></div>'
 specs=''.join(spec(*field) for field in fields)
 thumbs=''.join(f'<button type="button" data-src="{h(p["file"])}" data-alt="{E(title)} — {t("view","ракурс",l)} {i+1}" aria-label="{t("Show view","Показать ракурс",l)} {i+1}" aria-pressed="{str(i==0).lower()}"><img src="{h(p.get("thumbnail",p["file"]))}" alt="" width="90" height="72" loading="lazy"></button>' for i,p in enumerate(photos))


 related=sorted([x for x in items if x!=d],key=lambda x:(x['tracking']['key']!=d['tracking']['key'],abs(x['year']-d['year']) if x['year'] is not None and d['year'] is not None else float('inf')))[:6]
 description=d['description'][l] or t(f'{title}. Photographs and catalogue details of this mouse from Michael Pavlov’s collection.',f'{title}. Фотографии и характеристики мыши из коллекции Михаила Павлова.',l)
 body=f'''<nav class="breadcrumb" aria-label="{t('Breadcrumb','Путь к странице',l)}"><a href="{h(l+'/index.html')}">← {t('Catalogue','Каталог',l)}</a></nav><header class="specimen-heading"><h1>{E(title)}</h1><button class="share-trigger" id="forum-link" aria-label="{t('Share this mouse','Поделиться этой мышью',l)}" title="{t('Share','Поделиться',l)}" aria-haspopup="dialog"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 10.5 6.8-4M8.6 13.5l6.8 4"/></svg></button></header><article class="detail"><div class="gallery"><div class="main-photo"><button class="zoom" aria-label="{t('Enlarge photograph','Увеличить фотографию',l)}"><img id="main-image" src="{h(p0)}" alt="{E(title)} — {t('view','ракурс',l)} 1"></button></div><div class="photo-tools"><span id="photo-count">01 / {len(photos):02}</span><div><button data-step="-1" aria-label="{t('Previous photograph','Предыдущее фото',l)}">←</button><button data-step="1" aria-label="{t('Next photograph','Следующее фото',l)}">→</button></div></div><div class="thumbs">{thumbs}</div></div><div class="item-info">{description_html(d,l)}<h2 class="detail-section-title">{t('Details','Характеристики',l)}</h2><dl class="specs">{specs}</dl>{f'<p class="specimen-note">{E(d["notes"][l])}</p>' if d['notes'][l] else ''}{resources_html(d,l,journal.reference_links(d,l,path))}{wanted.exchange_link(d,l,path)}</div></article><section class="related"><div class="section-head"><h2>{t('Continue exploring','Другие экспонаты',l)}</h2><a href="{h(l+'/index.html')}">{t('All objects','Вся коллекция',l)} →</a></div><div class="grid">{''.join(card(x,l,path,i) for i,x in enumerate(related))}</div></section><dialog id="lightbox" aria-label="{t('Photograph viewer','Просмотр фотографии',l)}"><div class="dialog-head"><span>{E(title)}</span><button class="specimen-lightbox-close" data-close aria-label="{t('Close','Закрыть',l)}">×</button></div><img id="lightbox-image" src="{h(p0)}" alt="{E(title)}"><div class="actions"><button class="button" data-step="-1">← {t('Previous','Предыдущее',l)}</button><button class="button" data-step="1">{t('Next','Следующее',l)} →</button></div></dialog><dialog id="share" aria-labelledby="share-title"><div class="dialog-head"><h2 id="share-title">{t('Share this mouse','Поделиться этой мышью',l)}</h2><button data-close aria-label="{t('Close','Закрыть',l)}">×</button></div><div class="share-formats" role="group" aria-label="{t('Format','Формат',l)}"><button type="button" data-share-format="url" aria-pressed="true">{t('Link','Ссылка',l)}</button><button type="button" data-share-format="bbcode" aria-pressed="false">BBCode</button><button type="button" data-share-format="markdown" aria-pressed="false">Markdown</button><button type="button" data-share-format="image" aria-pressed="false">BBCode + {t('photo','фото',l)}</button></div><label class="sr-only" for="share-text">{t('Text to copy','Текст для копирования',l)}</label><div class="share-copy-field" id="copy-share" role="button" tabindex="0" aria-label="{t('Copy to clipboard','Скопировать в буфер обмена',l)}"><textarea id="share-text" readonly tabindex="-1"></textarea><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></svg></div><p class="status" id="share-status" aria-live="polite"></p></dialog>'''
 shell(path,l,title,description,body,objpath(d,'ru' if l=='en' else 'en'),p0)
for l in ('en','ru'):
 catalog(l,l+'/index.html')
 for d in items:detail(d,l)
 path=l+'/about/index.html';h=lambda p:link(path,p)
 body=f'''<article class="about"><h1>{t('A history of clicking.','История кликов.',l)}</h1><p>{t('I’m Michael Pavlov. I collect computer mice and trackballs: unusual mechanisms, unexpected shapes and the ideas behind the things we use every day.','Меня зовут Михаил Павлов. Я коллекционирую компьютерные мыши и трекболы: необычные механизмы, неожиданные формы и идеи, которые стоят за привычными вещами.',l)}</p><p>{t('Mouse Museum brings together photographs, catalogue records and stories about these devices. You can explore the collection, look inside individual mice and share links to the ones that catch your eye.','Mouse Museum объединяет фотографии, каталожные записи и истории об этих устройствах. Здесь можно изучить коллекцию, заглянуть внутрь отдельных мышей и поделиться тем, что заинтересовало.',l)}</p><section class="about-moscow" aria-labelledby="moscow-title"><h2 id="moscow-title">{t('Museum in Moscow','Музей в Москве',l)}</h2><p>{t('You can see part of my collection in person at the Museum of Computing in the Krasnokholmskaya Gallery. The exhibition brings together computer mice and trackballs from different eras alongside other computing devices.','Часть моей коллекции можно увидеть вживую в Музее вычислительной техники в галерее «Краснохолмская». В экспозиции — компьютерные мыши и трекболы разных эпох рядом с другой вычислительной техникой.',l)}</p><figure class="moscow-wide"><a href="{h('assets/about/moscow-display.webp')}" target="_blank" rel="noopener noreferrer" aria-label="{t('Open exhibition photograph','Открыть фотографию экспозиции',l)}"><img src="{h('assets/about/moscow-display.webp')}" width="1448" height="1086" loading="lazy" decoding="async" alt="{t('Computer mice in a glass display case at the Krasnokholmskaya Gallery','Компьютерные мыши в стеклянной витрине галереи «Краснохолмская»',l)}"></a><figcaption>{t('The collection in the Museum of Computing','Коллекция в Музее вычислительной техники',l)}</figcaption></figure><div class="moscow-visit"><figure><a href="{h('assets/about/moscow-cabinet.webp')}" target="_blank" rel="noopener noreferrer" aria-label="{t('Open display cabinet photograph','Открыть фотографию витрины',l)}"><img src="{h('assets/about/moscow-cabinet.webp')}" width="1086" height="1448" loading="lazy" decoding="async" alt="{t('A tall glass cabinet with mice and trackballs from the collection','Вертикальная витрина с мышами и трекболами из коллекции',l)}"></a></figure><div class="moscow-address"><span class="eyebrow">{t('Plan your visit','Как добраться',l)}</span><h3>{t('Krasnokholmskaya Gallery','Галерея «Краснохолмская»',l)}</h3><address>{t('Moscow, Krasnokholmskaya Embankment, 1/15','Москва, Краснохолмская набережная, 1/15',l)}<br>{t('Taganskaya metro station','Метро «Таганская»',l)}</address><a class="textlink" href="https://kholmy.vzmoscow.ru/techmus" target="_blank" rel="noopener noreferrer">{t('Exhibition on the gallery website','Выставка на сайте галереи',l)} ↗</a><p class="moscow-note">{t('See the gallery website for opening hours and tickets.','Часы работы и билеты — на сайте галереи.',l)}</p></div></div></section><section class="about-collaboration"><h2>{t('The collection travels.','Коллекция умеет приезжать.',l)}</h2><p>{t('The mice travel — and I come with them. I can bring the collection to an exhibition, festival or meetup, and give a talk about the history, design and mechanisms of computer mice.','Мыши путешествуют вместе со мной. Могу привезти коллекцию на выставку, фестиваль или встречу и провести лекцию об истории, дизайне и устройстве компьютерных мышей.',l)}</p><p>{t('Planning something? Have an idea for a collaboration? Feel free to ask — let’s see what we can do together.','Намечается движуха? Есть идея для коллаборации? Пишите — придумаем, что можно сделать вместе.',l)}</p><a class="about-email" href="mailto:mr.michael.pavlov@gmail.com">mr.michael.pavlov@gmail.com</a></section><div class="about-links"><a class="button primary" href="{h(l+'/index.html')}">{t('Explore the collection','Смотреть коллекцию',l)} →</a><a class="textlink" href="https://t.me/old_mice_and_hw" target="_blank" rel="noopener noreferrer">{t('Follow on Telegram','Канал в Telegram',l)} ↗</a></div></article>'''
 shell(path,l,t('About the museum','О музее',l),t('The computer mouse collection of Michael Pavlov.','Коллекция компьютерных мышей Михаила Павлова.',l),body,('ru' if l=='en' else 'en')+'/about/index.html')
journal.build(shell)
wanted.build(shell)
catalog('en','index.html')

# Unlisted collector landing; reuse the museum shell and catalogue assets.
from salemon import build as build_salemon
build_salemon(ROOT, OUT, items, shell, asset)
# The short Russian alias uses /ru/salemon/ as its canonical URL.
pages.remove('salemon/index.html')

# A static 404 with a base-aware homepage link; not a single-page app fallback.
base=urlparse(SITE).path.rstrip('/')+'/' if SITE else '/'
(OUT/'404.html').write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Not found — Mouse Museum</title><body style="font:18px Arial;padding:12vw;background:#f7f6f2">{METRIKA}<h1>Object not found / Страница не найдена</h1><p><a href="{E(base)}">Return to the collection / Вернуться к коллекции</a></p></body></html>')
if SITE:
 (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{E(public(p))}</loc></url>' for p in pages)+'</urlset>')
 (OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+SITE+'/sitemap.xml\n')
print(f'Built {len(pages)} pages and {sum(len(d["photos"]) for d in items)} photographs into {OUT}')
