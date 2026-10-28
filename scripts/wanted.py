"""Wanted and exchange pages. Entries stay separate from collection specimens."""
import html
import json
import posixpath
import re
from pathlib import Path
from urllib.parse import quote

EMAIL = 'mr.michael.pavlov@gmail.com'


def esc(value):
    return html.escape(str(value),quote=True)


def tr(en,ru,language):
    return ru if language=='ru' else en


def rel(path,target):
    return posixpath.relpath(target,posixpath.dirname(path) or '.')


class Wanted:
    def __init__(self,root,items,site=''):
        self.site=site
        self.items={item['slug']:item for item in items}
        self.slugs=set(self.items)
        self.wanted=self.load(root,'wanted','wanted')
        self.exchange=self.load(root,'exchange','available')

    def load(self,root,folder,status):
        entries=sorted([json.loads(file.read_text()) for file in (root/'content'/folder).glob('*.json')],key=lambda entry:entry['order'])
        seen=set()
        for index,entry in enumerate(entries):
            assert re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',entry['id'])
            assert entry['id'] not in seen,'Duplicate wanted/exchange ID'
            seen.add(entry['id'])
            assert entry['source'].startswith('https://')
            if folder=='exchange':
                assert entry.get('catalogueSlug') in self.items, f'Exchange entry needs a catalogue specimen: {entry["id"]}'
                item=self.items[entry['catalogueSlug']]
                assert item['source']==entry['source'], 'Exchange source does not match specimen'
                entry={**entry,'title':item['title'],'image':item['photos'][0]['file'],'thumbnail':item['thumbnail']}
                entries[index]=entry
            for key in ('image','thumbnail'):
                file=(root/entry[key]).resolve()
                assert file.is_relative_to(root/'assets') and file.is_file(),entry[key]
            if folder=='exchange':
                assert entry['title']['en'] and entry['title']['ru']
                assert entry['quantity'] is None or (isinstance(entry['quantity'],int) and entry['quantity']>0)
                assert not entry.get('catalogueSlug') or entry['catalogueSlug'] in self.slugs
        return [entry for entry in entries if entry.get('status')==status]

    @staticmethod
    def page_path(language,exchange=False):
        return f'{language}/wanted/'+('exchange/' if exchange else '')+'index.html'

    def mailto(self,entry,language,exchange=False):
        title=entry['title'][language] or entry['reference']
        source=entry['source']
        page=self.page_path(language,exchange)
        url=self.site+'/'+page.removesuffix('index.html')+'#'+entry['id'] if self.site else source
        if exchange:
            subject=tr('Mouse Museum — exchange: ','Mouse Museum — обмен: ',language)+title
            body=tr(f'Hello Michael!\n\nI am interested in exchanging for: {title}\n{url}\n\nI can offer in exchange: \nMy location: \nCondition and photos: ',f'Михаил, здравствуйте!\n\nИнтересует обмен на: {title}\n{url}\n\nМогу предложить взамен: \nМой город: \nСостояние и фотографии: ',language)
        else:
            subject=tr('Mouse Museum — wanted: ','Mouse Museum — предложение: ',language)+title
            body=tr(f'Hello Michael!\n\nI have a mouse from your wanted list: {title}\n{url}\n\nI would like to: donate / sell / exchange\nCondition and completeness: \nPrice or exchange proposal: \nMy location: \nPhotos: ',f'Михаил, здравствуйте!\n\nУ меня есть мышь из вашего списка: {title}\n{url}\n\nХочу: подарить / продать / обменять\nСостояние и комплектность: \nЦена или условия обмена: \nМой город: \nФотографии: ',language)
        return 'mailto:'+EMAIL+'?subject='+quote(subject,safe='')+'&body='+quote(body,safe='')

    def card(self,entry,language,path,exchange=False):
        title=entry['title'][language]
        alt=title or tr('Wanted mouse ','Искомая мышь ',language)+entry['reference']
        heading=f'<h2 title="{esc(title)}">{esc(title)}</h2>' if title else ''
        stock=''
        if exchange and entry['quantity']:
            stock=f'<span class="exchange-stock">{entry["quantity"]} {tr("available","шт.",language)}</span>'
        photo_class='wanted-photo'
        target=rel(path,entry['image'])
        label=alt+' — '+tr('enlarge photo','увеличить фото',language)
        if exchange:
            photo_class='exchange-photo'
            target=rel(path,f'{language}/mice/{entry["catalogueSlug"]}/index.html')
            label=alt
            heading=f'<h2 title="{esc(title)}"><a href="{target}">{esc(title)}</a></h2>'

        button=tr('Discuss an exchange','Обсудить обмен',language) if exchange else tr('I have one','У меня есть такая',language)
        return f'''<article class="wanted-card{' exchange-card' if exchange else ''}" id="{entry['id']}"><a class="{photo_class}" href="{target}" aria-label="{esc(label)}"><img src="{rel(path,entry['thumbnail'])}" alt="{esc(alt)}" loading="lazy">{stock}</a>{heading}<a class="button wanted-offer" href="{esc(self.mailto(entry,language,exchange))}" aria-label="{esc(button+': '+alt)}">{button}</a></article>'''

    def exchange_link(self,item,language,path):
        entry=next((entry for entry in self.exchange if entry.get('catalogueSlug')==item['slug']),None)
        if not entry:
            return ''
        url=rel(path,self.page_path(language,True))+'#'+entry['id']
        count=entry['quantity']
        stock=tr(f'{count} available',f'В наличии: {count} шт.',language) if count else tr('Available','Есть в наличии',language)
        return f'<section class="specimen-exchange"><div><h2>{tr("For exchange","Для обмена",language)}</h2><span>{stock}</span></div><a class="button exchange-propose" href="{esc(self.mailto(entry,language,True))}">{tr("Discuss an exchange","Обсудить обмен",language)}</a><a class="specimen-exchange-list" href="{url}">{tr("All exchange items","Весь обменный фонд",language)} →</a></section>'

    def build(self,shell):
        for language in ('en','ru'):
            for exchange in (False,True):
                entries=self.exchange if exchange else self.wanted
                path=self.page_path(language,exchange)
                wanted_url=rel(path,self.page_path(language))
                exchange_url=rel(path,self.page_path(language,True))
                tabs=f'''<nav class="wanted-tabs" aria-label="{tr('Wanted and exchange','Поиск и обмен',language)}"><a href="{wanted_url}" {'aria-current="page"' if not exchange else ''}>{tr('Looking for','Ищу',language)} <span>{len(self.wanted)}</span></a><a href="{exchange_url}" {'aria-current="page"' if exchange else ''}>{tr('For exchange','Для обмена',language)} <span>{len(self.exchange)}</span></a></nav>'''
                intro=tr('Have one of these mice? I would love to hear from you — whether you want to sell, donate or exchange it.','Есть такая мышь? Буду рад предложению — купить, принять в дар или обменять на что-то из моего обменного фонда.',language)
                if exchange:
                    intro=tr('Spare mice from my collection, available for exchange. If something catches your eye, let’s discuss what you could offer in return.','Лишние экземпляры из моей коллекции, которые готов обменять. Если что-то приглянулось — напишите, обсудим, что можно предложить взамен.',language)
                contact=tr('The button opens an email draft. You can also write directly to ','Кнопка откроет черновик письма. Можно написать напрямую: ',language)
                cards=''.join(self.card(entry,language,path,exchange) for entry in entries)
                empty=f'<p>{tr("Nothing listed here yet.","Пока здесь ничего нет.",language)}</p>' if not entries else ''
                body=f'''<section class="wanted-heading"><h1>Wanted<span> / {tr('Exchange','Обмен',language)}</span></h1><p>{intro}</p></section>{tabs}<div class="wanted-grid">{cards}{empty}</div><p class="wanted-contact">{contact}<a href="mailto:{EMAIL}">{EMAIL}</a>.</p>'''
                title=tr('For exchange','Обменный фонд',language) if exchange else tr('Wanted','Ищу в коллекцию',language)
                other=self.page_path('ru' if language=='en' else 'en',exchange)
                shell(path,language,title,intro,body,other,entries[0]['image'] if entries else None)
