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


def viewing_location(item,language):
    # Explicit empty values allow the owner to hide a legacy location.
    if 'whereToSee' in item:
        value=localized(item['whereToSee'],language)
        return 'Local' if value.lower()=='local' else value
    raw=item.get('sourceProperties',{}).get('Где посмотреть','')
    translations={'Краснохолмская':'Krasnokholmskaya Gallery','Демо Витрина':'Demo display case',
                  'Демо Стол':'Demo table','Ближний':'Near','Дальний':'Far','Средний':'Middle',
                  'Ближайший':'Nearest'}
    return translations.get(raw,raw) if language=='en' else raw


def viewing_location_key(item):
    """Use the same stored value in filter URLs across both languages."""
    key=viewing_location(item,'ru') or viewing_location(item,'en') or 'unknown'
    return 'local' if key.lower()=='local' else key


def validate_extras(item):
    channel_posts(item)
    for link in item.get('externalLinks',[]):
        validate_url(link['url'])
        assert localized(link.get('title'),'en') and localized(link.get('title'),'ru'), 'External links need labels in both languages'
    for language in ('en','ru'):
        assert isinstance(localized(item.get('description',{}),language),str)
        assert isinstance(viewing_location(item,language),str)


def description_html(item,language):
    text=localized(item.get('description',{}),language).strip()
    if not text:
        return ''
    paragraphs=''.join('<p>'+esc(part).replace('\n','<br>')+'</p>' for part in re.split(r'\n\s*\n',text) if part.strip())
    return f'<section class="specimen-description"><h2>{tr("About this specimen","Об экземпляре",language)}</h2>{paragraphs}</section>'


def resources_html(item,language):
    resources=[]
    links=list(item.get('externalLinks',[]))
    source=item.get('source')
    if source and not any(link['url'].rstrip('/')==source.rstrip('/') for link in links):
        links.append({'url':source,'title':{'en':'Original catalogue record','ru':'Запись на Коллекционерусе'}})
    for link in links:
        url=validate_url(link['url'])
        title=localized(link['title'],language)
        host=urlsplit(url).hostname.removeprefix('www.')
        resources.append(f'<li><a href="{esc(url)}" target="_blank" rel="noopener noreferrer"><span>{esc(title)}</span><small>{esc(host)} ↗</small></a></li>')
    result=''
    if resources:
        result=f'<section class="specimen-resources"><h2>{tr("Links & references","Ссылки и материалы",language)}</h2><ul>'+''.join(resources)+'</ul></section>'
    posts=channel_posts(item)
    if posts:
        links=''.join(f'<li><a href="{esc(url)}" target="_blank" rel="noopener noreferrer"><span>{tr("Post on Telegram","Пост в канале",language)}</span><small>№{esc(urlsplit(url).path.rstrip("/").rsplit("/",1)[-1])} ↗</small></a></li>' for url in posts)
        result+=f'<section class="specimen-resources specimen-telegram"><h2>Telegram</h2><ul>{links}</ul></section>'
    return result
