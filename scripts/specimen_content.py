"""Optional specimen text, reference links and legacy source fields."""
import html
import re
from urllib.parse import urlsplit


def esc(value):
    return html.escape(str(value),quote=True)


def tr(en,ru,language):
    return ru if language=='ru' else en


def localized(value,language):
    return value.get(language,'') if isinstance(value,dict) else value or ''


def validate_url(url):
    parsed=urlsplit(url)
    assert parsed.scheme in ('http','https') and parsed.netloc, f'Invalid specimen link: {url}'
    return url


def channel_posts(item):
    explicit=item.get('channelPost')
    if 'channelPost' in item:
        urls=([explicit] if isinstance(explicit,str) else explicit) if explicit else []
    else:
        source=item.get('sourceProperties',{}).get('Пост в канале','')
        urls=re.findall(r'(?:https?://)?(?:t\.me|telegram\.me)/[A-Za-z0-9_]+/\d+(?:\?[^\s<>]+)?',source)
    result=[]
    for url in urls:
        if not url.startswith(('http://','https://')):
            url='https://'+url
        validate_url(url)
        parsed=urlsplit(url)
        assert parsed.hostname in ('t.me','telegram.me'), 'channelPost must link to Telegram'
        assert re.fullmatch(r'/[A-Za-z0-9_]+/\d+/?',parsed.path), 'channelPost must identify a post'
        if url not in result:
            result.append(url)
    return result


VIEWING_LOCATIONS={
    'Краснохолмская':'Krasnokholmskaya Gallery','Демо Витрина':'Demo display case',
    'Демо Стол':'Demo table','Ближний':'Near','Дальний':'Far','Средний':'Middle',
    'Ближайший':'Nearest','Local':'Local'}


def location_choices():
    return [{'ru':ru,'en':en} for ru,en in VIEWING_LOCATIONS.items()]


def location_pair(value):
    """Store one catalogue location. The English label always comes from the pair."""
    if not isinstance(value,dict):
        raise ValueError('location')
    ru=value.get('ru')
    en=value.get('en')
    if not isinstance(ru,str) or not isinstance(en,str):
        raise ValueError('location')
    ru,en=ru.strip(),en.strip()
    if ru.lower()=='local' or (not ru and en.lower()=='local'):
        ru='Local'
    if ru.lower() in ('','unknown') and en.lower() in ('','unknown'):
        return {'ru':'','en':''}
    if ru not in VIEWING_LOCATIONS:
        raise ValueError(ru)
    return {'ru':ru,'en':VIEWING_LOCATIONS[ru]}


def viewing_location(item,language):
    # Explicit empty values allow the owner to hide a legacy location.
    if 'whereToSee' in item:
        value=localized(item['whereToSee'],language)
        return 'Local' if value.lower()=='local' else value
    raw=item.get('sourceProperties',{}).get('Где посмотреть','')
    return VIEWING_LOCATIONS.get(raw,raw) if language=='en' else raw


def viewing_location_key(item):
    """Use the same stored value in filter URLs across both languages."""
    key=viewing_location(item,'ru') or viewing_location(item,'en') or 'unknown'
    return 'local' if key.lower()=='local' else key


def validate_extras(item):
    channel_posts(item)
    for link in item.get('externalLinks',[]):
        validate_url(link['url'])
        title=link.get('title')
        assert isinstance(title,dict) and all(isinstance(title.get(language),str) for language in ('en','ru'))
    for language in ('en','ru'):
        assert isinstance(localized(item.get('description',{}),language),str)
        assert isinstance(viewing_location(item,language),str)


def description_html(item,language):
    text=localized(item.get('description',{}),language).strip()
    if not text:
        return ''
    paragraphs=''.join('<p>'+esc(part).replace('\n','<br>')+'</p>' for part in re.split(r'\n\s*\n',text) if part.strip())
    return f'<section class="specimen-description"><h2>{tr("About this model","Об этой модели",language)}</h2>{paragraphs}</section>'


def resources_html(item,language,publications=()):
    resources=[]
    seen=set()
    for publication in publications:
        url=publication['url']
        seen.add(url.rstrip('/'))
        resources.append(f'<li><a href="{esc(url)}"><span>{esc(publication["title"])}</span><small>{esc(publication["source"])}</small></a></li>')
    links=list(item.get('externalLinks',[]))
    for url in channel_posts(item):
        links.append({'url':url,'title':{'en':'Post on Telegram','ru':'Пост в канале'}})
    if item.get('source'):
        links.append({'url':item['source'],'title':{'en':'Original catalogue record','ru':'Запись на Коллекционерусе'}})
    for link in links:
        url=validate_url(link['url'])
        if url.rstrip('/') in seen:
            continue
        seen.add(url.rstrip('/'))
        host=urlsplit(url).hostname.removeprefix('www.')
        title=localized(link['title'],language).strip() or host
        resources.append(f'<li><a href="{esc(url)}" target="_blank" rel="noopener noreferrer"><span>{esc(title)}</span><small>{esc(host)}</small></a></li>')
    if not resources:
        return ''
    return f'<section class="specimen-resources"><h2>{tr("Materials","Материалы",language)}</h2><ul>'+''.join(resources)+'</ul></section>'
