#!/usr/bin/env python3
"""Plan/apply a complete import of existing Collectionerus specimens.

Network is separate: use curl with generated config files. New specimens are
staged by import_catalogue.py. Existing slugs, IDs, notes and journal links are preserved.
Import-only dependencies: BeautifulSoup and Pillow; not needed for site builds.
"""
import argparse
import hashlib
import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
BASE='https://collectionerus.ru'
NOW=lambda:datetime.now(ZoneInfo('Europe/Moscow')).isoformat(timespec='seconds')

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parse_page(page,item):
    soup=BeautifulSoup(page.read_text(),'html.parser')
    assert soup.h1 and soup.select_one('.item-properties'),f'Invalid source page: {page}'
    properties={}
    property_links={}
    for p in soup.select('.item-properties p'):
        label=p.get_text(' ',strip=True).split(':',1)[0].strip()
        value=p.get_text(' ',strip=True).partition(':')[2].strip()
        if not label or not value:continue
        # Responsive alternatives repeat visible link labels; take the full value once.
        for spans in p.select('.showfirstfit'):
            children=spans.find_all('span',recursive=False)
            if children:
                spans.replace_with(children[0].get_text())
        properties[label]=p.get_text(' ',strip=True).partition(':')[2].strip()
        property_links[label]=list(dict.fromkeys(urljoin(BASE,a['href']) for a in p.select('a[href]') if not a['href'].startswith('#')))
    description=soup.select_one('.item-description:not(.image-description)')
    raw_description=str(description) if description else ''
    links=[]
    if description:
        for a in description.select('a[href]'):
            url=urljoin(BASE,a['href'])
            if urlsplit(url).scheme not in ('https','http'):continue
            text=a.get_text(' ',strip=True)
            paragraph=a.find_parent('p')
            context=paragraph.get_text(' ',strip=True) if paragraph else ''
            links.append({'url':url,'sourceLabel':text,'context':context})
        # Keep actual prose; bare URL lists become externalLinks, not duplicate text.
        for a in description.select('a[href]'):
            text=a.get_text(' ',strip=True)
            if text.startswith(('https://','http://')) or text==urlsplit(a['href']).netloc:
                a.decompose()
            else:
                a.unwrap()
        for br in description.select('br'):br.replace_with('\n')
        paragraphs=description.select('p')
        text='\n\n'.join(p.get_text(' ',strip=True).strip() for p in paragraphs) if paragraphs else description.get_text(' ',strip=True)
        text='\n\n'.join(p for p in re.split(r'\n\s*\n',text) if p.strip() and p.strip() not in ('Мануал','Manual'))
    else:text=''
    photos=[]
    for i,li in enumerate(soup.select('.item-thumbnails li[data-original-src]'),1):
        original=urljoin(BASE,li['data-original-src'])
        source=urljoin(BASE,li.get('data-src',li['data-original-src']))
        suffix=Path(urlsplit(original).path).suffix.lower() or '.img'
        photos.append({'position':i,'source':source,'originalSource':original,'originalName':Path(urlsplit(original).path).name,
                       'cacheFile':f'photos/{item["slug"]}/{i:02}{suffix}',
                       'caption':li.get('data-description',''),'sourceSizeLabel':li.get('data-size','')})
    assert photos,f'No original photographs: {page}'
    assert len(photos)==len(soup.select('.item-thumbnails li')),f'Incomplete gallery: {page}'
    return {'sourceId':int(page.stem),'source':item['source'],'slug':item['slug'],
            'sourceTitle':soup.h1.get_text(' ',strip=True),'retrievedAt':datetime.fromtimestamp(page.stat().st_mtime,ZoneInfo('Europe/Moscow')).isoformat(timespec='seconds'),
            'sourcePageSha256':digest(page),'descriptionHtml':raw_description,'descriptionText':text,
            'externalLinks':links,'properties':properties,'propertyLinks':property_links,'photos':photos}

TRACKS={
 'оптический через коврик':('optical-pad','Optical · special pad'),
 'на потенциометрах':('potentiometer','Potentiometers'),
 'оптико-механический (классика)':('ball','Optomechanical ball'),
 'оптико-механический (особенный)':('ball-special','Optomechanical · special mechanism'),
 'на дискретных датчиках':('discrete','Discrete sensors'),
 'на дискретных датчиках (hawley)':('discrete-hawley','Discrete sensors (Hawley)'),
 'на датчиках с осевым наклоном (hawley)':('hawley-tilt','Axial tilt sensors (Hawley)'),
 'на дискретных датчиках (особенный)':('discrete-special','Discrete sensors · special mechanism'),
 'оптический (классика)':('optical','Optical'),
 'емкостный':('capacitive','Capacitive'),
 'оптические поворотные энкодеры':('optical-rotary','Optical rotary encoders'),
 'линейные оптические энкодеры':('optical-linear','Linear optical encoders'),
}
LOCATIONS={'Краснохолмская':'Krasnokholmskaya Gallery','Демо Витрина':'Demo display case','Демо Стол':'Demo table',
           'Ближний':'Near','Дальний':'Far','Средний':'Middle','Ближайший':'Nearest','unknown':'Unknown','Local':'Local','local':'Local'}
TRANSLATIONS={
 'Первая мышь с колесиком':'The first mouse with a scroll wheel.',
 'Корвет':'Korvet.',
 'Мышка Минского завода ЭВМ к компьютеру ЕС 1849':'A mouse made by the Minsk Computer Plant for the ES 1849 computer.',
 'КОМПьютеры Академии Наук':'Computers of the Academy of Sciences (the name combines the Russian words).',
 'Sinclair QL interface':'Sinclair QL interface.',
 'Для Apricot QI-300\n\nLogitech M8 (M8-2F-25F)':'For the Apricot QI-300.\n\nLogitech M8 (M8-2F-25F)',
 'Манипулятор от корабельного зенитно-ракетного комплекса Ураган.':'A pointing device from the naval Uragan surface-to-air missile system.',
 '(коробка в Демо Стол)':'(Box at Demo table.)',
 'Выдвигающаяся мышка, встроенная в ноутбуки OmniBook и серию InternetAdvisor':'A retractable mouse built into OmniBook laptops and the InternetAdvisor series.',
 'Прототип первой мыши (реплика)':'A replica of the first mouse prototype.',
 "От приставки Киборд-003 Simba's":"From the Kibord-003 Simba’s console.",
}
FEATURES={'Металлический шарик':'Metal ball','два в одном':'Two-in-one design','Беспроводная, радио':'Wireless · radio','Беспроводная , радио':'Wireless · radio','Шнур сзади':'Rear cable','встроенный модем':'Built-in modem','Беспроводная , ИК':'Wireless · infrared','Кнопки не кнопки':'Unconventional buttons'}
MANUFACTURERS={'СССР':'USSR / manufacturer not specified','Минский завод ЭВМ':'Minsk Computer Plant','КБ Марс':'Mars Design Bureau','СПЗ им. В.И.Ленина':'SPZ named after V. I. Lenin','ПО Комета':'Kometa Production Association','НПО «Алмаз»':'NPO Almaz','ТК Мехатроника, ЗПК-Габрово':'TK Mechatronics, ZPK Gabrovo','НПО «Агат»':'NPO Agat'}
LINK_LABELS={
 'https://www.youtube.com/watch?v=tcGowuMOpVo':('Video on YouTube','Видео на YouTube'),
 'https://www.youtube.com/watch?v=KJyjaapf0Ag':('Video on YouTube','Видео на YouTube'),
 'https://www.youtube.com/watch?v=-OSXeNVM3UI':('Video on YouTube','Видео на YouTube'),
 'https://trackballs.eu/media/IBM/1396670/PC%20Mag%20Oct%201991%20p126.pdf':('PC Magazine, October 1991 · p. 126 · PDF','PC Magazine, октябрь 1991 · стр. 126 · PDF'),
 'https://en.wikipedia.org/wiki/Blit_(computer_terminal)':('Blit computer terminal · Wikipedia','Терминал Blit · Wikipedia'),
}

def plan(cache):
    config=[];snapshots=[]
    override_file=ROOT/'data/source/download-overrides.json'
    overrides=json.loads(override_file.read_text()) if override_file.exists() else {}
    files=sorted((ROOT/'content/mice').glob('*.json'))
    existing_names={p.name for p in files}
    files+=sorted(p for p in (cache/'new-items').glob('*.json') if p.name not in existing_names)
    baseline_file=cache/'catalogue-baseline.json'
    baseline=json.loads(baseline_file.read_text()) if baseline_file.exists() else None
    for file in files:
        item=json.loads(file.read_text());ident=item['source'].rstrip('/').rsplit('/',1)[-1]
        snapshot=parse_page(cache/'pages'/f'{ident}.html',item);snapshot['itemFile']='content/mice/'+file.name
        snapshot['previousPhotoCount']=baseline.get(item['source'],0) if baseline is not None else len(item['photos'])
        if not file.is_relative_to(ROOT):snapshot['seedFile']=str(file)
        snapshots.append(snapshot)
        for photo in snapshot['photos']:
            photo.update(overrides.get(photo['originalSource'],{}))
            target=cache/photo['cacheFile'];target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.stat().st_size:
                try:
                    with Image.open(target) as image:image.load()
                    continue
                except (OSError,ValueError):
                    pass
            config+=['url = '+json.dumps(photo.get('downloadSource',photo['originalSource'])),'output = '+json.dumps(str(target))]
    write_json(cache/'plan.json',snapshots)
    (cache/'originals.conf').write_text('\n'.join(config))
    print(json.dumps({'specimens':len(snapshots),'photos':sum(len(s['photos']) for s in snapshots),'toDownload':len(config)//2},ensure_ascii=False))


def apply(cache):
    snapshots=json.loads((cache/'plan.json').read_text())
    # Verify all downloads before changing any public specimen data.
    for snapshot in snapshots:
        for photo in snapshot['photos']:
            file=cache/photo['cacheFile']
            assert file.is_file() and file.stat().st_size>0,f'Missing original: {file}'
            with Image.open(file) as image:
                image.load()
                expected=re.match(r'(\d+)[×x](\d+)',photo['sourceSizeLabel'])
                if expected and photo.get('originalAvailable',True):
                    assert sorted(image.size)==sorted(map(int,expected.groups())),f'Original resolution differs from source: {file}'
    report=[]
    for snapshot in snapshots:
        item_file=ROOT/snapshot['itemFile'];item=json.loads((item_file if item_file.exists() else Path(snapshot['seedFile'])).read_text());previous_count=snapshot.get('previousPhotoCount',len(item['photos']))
        props=snapshot['properties'];prior_props=item.get('sourceProperties',{})
        item['sourceProperties']=props
        item['sourceTitle']=snapshot['sourceTitle']
        item['year']=int(props['Год']) if props.get('Год') else None
        manufacturer=props.get('Производитель','')
        item['manufacturer']={'ru':manufacturer or 'Не указан','en':MANUFACTURERS.get(manufacturer,manufacturer) or 'Not recorded'}
        item['brand']=manufacturer or 'Unknown'
        tracking=props.get('Способ позиционирования','')
        assert not tracking or tracking.lower() in TRACKS,f'Unmapped tracking: {tracking}'
        key,en=TRACKS.get(tracking.lower(),('unknown','Not recorded'))
        item['tracking']={'key':key,'ru':tracking or 'Не указана','en':en}
        item['interface']=props.get('Интерфейс') or None
        item['soviet']=props.get('СССР','').lower()=='да'
        features=props.get('Особенности','')
        old=item.get('features',{})
        item['features']={'ru':features,'en':old.get('en') if features==prior_props.get('Особенности','') and old.get('en') else FEATURES.get(features,features)}
        location=props.get('Где посмотреть','')
        item['whereToSee']={'ru':location,'en':LOCATIONS.get(location,location)}
        board=props.get('Производитель платы','')
        item['boardManufacturer']={'ru':board,'en':MANUFACTURERS.get(board,board)}
        channel=snapshot['propertyLinks'].get('Пост в канале',[])
        item['channelPost']=channel[0] if len(channel)==1 else channel
        text=snapshot['descriptionText']
        assert not text or text in TRANSLATIONS or not re.search('[А-Яа-я]',text),f'Description needs translation: {snapshot["sourceId"]}: {text}'
        item['description']={'ru':text,'en':TRANSLATIONS.get(text,text)}
        existing_links={link['url']:link for link in item.get('externalLinks',[])}
        links=[];seen=set()
        for link in snapshot['externalLinks']:
            url=link['url']
            if url in seen:continue
            seen.add(url)
            if url in existing_links:links.append(existing_links[url]);continue
            label=LINK_LABELS.get(url)
            if not label:
                name=link['sourceLabel']
                if name.startswith(('https://','http://')):name=urlsplit(url).hostname.removeprefix('www.')
                label=(name,name)
            links.append({'url':url,'title':{'en':label[0],'ru':label[1]}})
        item['externalLinks']=links
        folder=ROOT/'assets/photos'/item['slug'];originals=folder/'originals';originals.mkdir(parents=True,exist_ok=True)
        old_photos={photo.get('originalSource'):photo for photo in item.get('photos',[])}
        def prepare_photo(photo):
            prior=old_photos.get(photo['originalSource'])
            if prior and all((ROOT/prior.get(key,'__missing__')).is_file() for key in ('original','file','thumbnail')) and digest(cache/photo['cacheFile'])==prior.get('sha256') and digest(ROOT/prior['original'])==prior['sha256']:
                return prior
            i=photo['position'];cached=cache/photo['cacheFile'];suffix=cached.suffix
            original_folder=originals if photo.get('originalAvailable',True) else folder/'source-images'
            original_folder.mkdir(parents=True,exist_ok=True)
            original=original_folder/f'{i:02}{suffix}'
            shutil.copy2(cached,original)
            original_hash=digest(original);assert original_hash==digest(cached)
            with Image.open(original) as raw:
                ow,oh=raw.size;image=ImageOps.exif_transpose(raw)
                if image.mode not in ('RGB','RGBA'):image=image.convert('RGB')
                image.thumbnail((2400,2400),Image.Resampling.LANCZOS)
                display=folder/f'{i:02}.webp';image.save(display,'WEBP',quality=80,method=6)
                width,height=image.size
                thumb=folder/f'{i:02}-thumb.webp';small=image.copy();small.thumbnail((240,180),Image.Resampling.LANCZOS);small.save(thumb,'WEBP',quality=84)
                if i==1:
                    cover=image.copy();cover.thumbnail((640,480),Image.Resampling.LANCZOS);cover.save(folder/'thumb.webp','WEBP',quality=86)
            size=original.stat().st_size
            record={'file':display.relative_to(ROOT).as_posix(),'thumbnail':thumb.relative_to(ROOT).as_posix(),
                    'original':original.relative_to(ROOT).as_posix(),'source':photo['source'],'originalSource':photo['originalSource'],
                    'originalAvailable':photo.get('originalAvailable',True),'downloadSource':photo.get('downloadSource',photo['originalSource']),
                    'sourceOriginalError':photo.get('sourceOriginalError',''),'originalFilename':photo['originalName'],'width':width,'height':height,
                    'originalWidth':ow,'originalHeight':oh,'originalBytes':size,'sha256':original_hash,'caption':photo['caption']}
            return record
        with ThreadPoolExecutor(max_workers=4) as pool:
            photos=list(pool.map(prepare_photo,snapshot['photos']))
        total_bytes=sum(photo['originalBytes'] for photo in photos)
        item['photos']=photos;item['thumbnail']=(folder/'thumb.webp').relative_to(ROOT).as_posix()
        item['sourceSync']={'retrievedAt':snapshot['retrievedAt'],'sourcePhotoCount':len(snapshot['photos']),
                            'sourceDescriptionPresent':bool(snapshot['descriptionText'] or snapshot['externalLinks']),
                            'sourcePropertyCount':len(props),'availableOriginals':sum(p.get('originalAvailable',True) for p in photos)}
        write_json(item_file,item)
        # Full source metadata is retained separately, including original prose/links.
        write_json(ROOT/'data/source/collectionerus'/f'{snapshot["sourceId"]}.json',{k:v for k,v in snapshot.items() if k!='seedFile'})
        # Refresh quantity without creating another collection specimen.
        for exchange_file in (ROOT/'content/exchange').glob('*.json'):
            exchange=json.loads(exchange_file.read_text())
            if exchange.get('catalogueSlug')!=item['slug']:continue
            stock=props.get('Обменный фонд','');exchange['sourceStock']=stock
            match=re.search(r'\d+',stock)
            exchange['quantity']=int(match[0]) if match else None
            exchange['status']='available' if 'есть' in stock.lower() else 'exchanged'
            write_json(exchange_file,exchange)
        report.append({'sourceId':snapshot['sourceId'],'slug':item['slug'],'title':item['title']['ru'],
                       'previousPhotos':previous_count,'sourcePhotos':len(snapshot['photos']),'localOriginals':len(photos),
                       'originalBytes':total_bytes,'availableOriginals':sum(p.get('originalAvailable',True) for p in photos),'descriptionTextPresent':bool(text),'externalLinks':len(links),
                       'sourcePropertyCount':len(props),'missingSourceFields':[label for label in ['Производитель','Год','Способ позиционирования','Интерфейс'] if not props.get(label)]})
        print(f'{snapshot["sourceId"]}: {previous_count} → {len(photos)} photos',flush=True)
    unavailable=[{'sourceId':record['sourceId'],'slug':record['slug'],'position':photo['position'],'originalSource':photo['originalSource'],'downloadSource':photo['downloadSource'],'error':photo['sourceOriginalError']} for record in snapshots for photo in record['photos'] if not photo.get('originalAvailable',True)]
    result={'availableOriginals':sum(r['availableOriginals'] for r in report),'unavailableOriginals':unavailable,'completedAt':NOW(),'specimens':len(report),'photos':sum(r['sourcePhotos'] for r in report),
            'originalBytes':sum(r['originalBytes'] for r in report),'entries':report}
    index_file=cache/'catalogue-index.json'
    if index_file.exists():
        index=json.loads(index_file.read_text())
        assert {r['source'] for r in index}=={s['source'] for s in snapshots}, 'Complete catalogue index mismatch'
        write_json(ROOT/'data/source/catalogue-index.json',{'retrievedAt':NOW(),'count':len(index),'entries':index})
    write_json(ROOT/'reports/collectionerus-sync.json',result)
    table=['# Сверка с исходным каталогом','',f'Обновлено: {result["completedAt"]}',
           f'Экспонатов: {len(report)}. Фотографий: {result["photos"]}. Оригиналы: {result["originalBytes"]/1024**2:.1f} МиБ.','',
           'Скачанные файлы источника сохранены без перекодирования, проверены декодированием и SHA-256. Превью созданы отдельно. Исключения по недоступным оригиналам перечислены ниже. Прочерки в таблице означают отсутствие сведений в источнике.','',
           '| ID | Экспонат | Фото было → стало | Текст | Ссылки | Не заполнено в источнике |',
           '| --- | --- | --- | --- | --- | --- |']
    for r in sorted(report,key=lambda r:r['sourceId']):
        table.append(f'| {r["sourceId"]} | {r["title"]} | {r["previousPhotos"]} → {r["sourcePhotos"]} | {"есть" if r["descriptionTextPresent"] else "—"} | {r["externalLinks"]} | {", ".join(r["missingSourceFields"]) or "—"} |')
    if unavailable:
        table+=['','## Оригиналы, недоступные в источнике','']
        for row in unavailable:table.append(f'- ID {row["sourceId"]}, фото {row["position"]}: оригинал вернул HTTP 403. Сохранено доступное изображение со страницы: {row["downloadSource"]}. Исходная ссылка на оригинал: {row["originalSource"]}.')
    (ROOT/'reports/collectionerus-sync.md').write_text('\n'.join(table)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='entries'},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('plan','apply'))
    parser.add_argument('--cache',type=Path,required=True)
    args=parser.parse_args()
    (plan if args.stage=='plan' else apply)(args.cache)
