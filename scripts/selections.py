"""Selection content validation and rendering; shared by journal and local editor."""
import html
import json
import posixpath
import re
from datetime import datetime

SLUG = r'[a-z0-9]+(?:-[a-z0-9]+)*'
E = html.escape
LABELS = {
    'ru': {'share': 'Поделиться подборкой', 'share_short': 'Поделиться', 'close': 'Закрыть', 'link': 'Ссылка на подборку', 'copy': 'Скопировать ссылку', 'enlarge': 'Увеличить фото', 'card': 'Карточка экспоната', 'viewer': 'Фотографии подборки', 'prev': 'Предыдущее', 'next': 'Следующее'},
    'en': {'share': 'Share this selection', 'share_short': 'Share', 'close': 'Close', 'link': 'Link to this selection', 'copy': 'Copy link', 'enlarge': 'Enlarge photo', 'card': 'Exhibit card', 'viewer': 'Selection photos', 'prev': 'Previous', 'next': 'Next'},
}


def text_of(value, lang='ru'):
    if isinstance(value, dict):
        chosen = value.get(lang)
        if isinstance(chosen, str) and chosen.strip():
            return chosen
        fallback = value.get('ru')
        return fallback if isinstance(fallback, str) else ''
    return value if isinstance(value, str) else ''


def _copy_ok(value, required=False):
    if isinstance(value, str):
        return bool(value.strip()) if required else True
    if isinstance(value, dict) and isinstance(value.get('ru'), str) and isinstance(value.get('en'), str):
        return bool(value['ru'].strip()) if required else True
    return False


def validate(data, items, root):
    if not isinstance(data, dict) or not re.fullmatch(SLUG, data.get('slug', '')):
        raise ValueError('Некорректный адрес подборки.')
    datetime.fromisoformat(data.get('date', ''))
    if not _copy_ok(data.get('title'), required=True):
        raise ValueError('Заполните название подборки.')
    if not _copy_ok(data.get('intro', ''), required=False):
        raise ValueError('Вступление подборки должно быть текстом.')
    if 'listed' in data and not isinstance(data['listed'], bool):
        raise ValueError('Поле listed должно быть логическим.')
    if not isinstance(data.get('entries'), list) or not 1 <= len(data['entries']) <= 200:
        raise ValueError('Добавьте от 1 до 200 карточек.')
    for entry in data['entries']:
        if not isinstance(entry, dict) or not _copy_ok(entry.get('text')):
            raise ValueError('Для карточки нужен текст.')
        if entry.get('kind') == 'specimen':
            item = items.get(entry.get('specimen'))
            if item is None:
                raise ValueError('Экспонат не найден в коллекции.')
            photo = entry.get('photo')
            if photo is not None and photo not in {p['file'] for p in item['photos']}:
                raise ValueError('Выберите фотографию этого экспоната.')
        elif entry.get('kind') == 'photo':
            if not _copy_ok(entry.get('title', ''), required=False):
                raise ValueError('Название фотографии должно быть текстом.')
            if not isinstance(entry.get('year', ''), str) or len(entry.get('year', '')) > 40:
                raise ValueError('Некорректный год фотографии.')
            if not _copy_ok(entry.get('credit', '')):
                raise ValueError('Подпись источника должна быть текстом.')
            file = entry.get('photo')
            if not isinstance(file, str):
                raise ValueError('Загрузите фотографию.')
            target = (root / file).resolve()
            if not target.is_relative_to((root / 'assets').resolve()) or not target.is_file() or target.suffix.lower() not in ('.webp', '.jpg', '.jpeg', '.png'):
                raise ValueError('Фотография не найдена.')
        else:
            raise ValueError('Неизвестный тип карточки.')


def specimen_photo(item, chosen):
    files = [photo['file'] for photo in item['photos']]
    return chosen if chosen in files else files[0]


def resolve(entry, items, lang='ru'):
    text = text_of(entry.get('text'), lang)
    if entry['kind'] == 'specimen':
        item = items[entry['specimen']]
        return dict(entry, title=item['title'][lang], year=str(item.get('year') or ''),
                    photo=specimen_photo(item, entry.get('photo')), url=f'{lang}/mice/{item["slug"]}/index.html', credit='', text=text)
    return dict(entry, title=text_of(entry.get('title'), lang), text=text, credit=text_of(entry.get('credit'), lang), url='', year=entry.get('year', ''))


def posts(root, items):
    result = []
    for path in (root / 'content/selections').glob('*.json'):
        data = json.loads(path.read_text())
        validate(data, items, root)
        rows = [resolve(e, items) for e in data['entries']]
        result.append(dict(data, selection=data, category='selection', source='',
                           title={lang: text_of(data['title'], lang) for lang in ('ru', 'en')},
                           excerpt={lang: text_of(data['intro'], lang) for lang in ('ru', 'en')},
                           cover=rows[0]['photo'], relatedItems=list(dict.fromkeys(e['specimen'] for e in data['entries'] if e['kind'] == 'specimen'))))
    return result


def paras(text):
    return ''.join('<p>' + E(p).replace('\n', '<br>') + '</p>' for p in re.split(r'\n\s*\n', text.strip()) if p)


def cover(post, items, lang, path):
    h = lambda target: posixpath.relpath(target, posixpath.dirname(path))
    rows = [resolve(e, items, lang) for e in post['selection']['entries'][:4]]
    return '<div class="journal-cover selection-cover">' + ''.join(f'<img src="{E(h(e["photo"]))}" alt="{E(e["title"])}" loading="lazy">' for e in rows) + '</div>'


def article(post, items, lang, shell):
    data = post['selection']
    title, intro = text_of(data['title'], lang), text_of(data['intro'], lang)
    labels = LABELS[lang]
    path = f'{lang}/journal/{data["slug"]}/index.html'
    h = lambda target: posixpath.relpath(target, posixpath.dirname(path))
    rooted = lambda target: '../' * path.count('/') + target
    rows = []
    for e in data['entries']:
        entry = resolve(e, items, lang)
        caption = E(entry['title'])
        href = rooted(entry['url']) if entry['url'] else ''
        link = f'<a class="selection-link" href="{href}">{caption}</a>' if href else f'<span class="selection-link selection-unlinked">{caption}</span>'
        credit = '<p class="selection-credit">' + E(entry['credit']) + '</p>' if entry['credit'] else ''
        enlarge = f"{E(labels['enlarge'])}: {caption}" if entry['title'] else E(labels['enlarge'])
        caption_html = f'<div class="selection-caption">{link}<span class="selection-year">{E(entry["year"])}</span></div>' if entry['title'] or entry['year'] else ''
        copy_html = f'<div class="selection-copy">{paras(entry["text"])}</div>' if entry['text'].strip() else ''
        rows.append(f'''<article class="selection-item"><button class="selection-photo" data-full="{E(h(entry['photo']))}" data-title="{caption}" data-specimen="{E(href)}" aria-label="{enlarge}"><img src="{E(h(entry['photo']))}" alt="{caption}" loading="lazy"></button>{caption_html}{copy_html}{credit}</article>''')
    share = f'''<button type="button" class="share-trigger" data-selection-share aria-label="{E(labels['share'])}" title="{E(labels['share_short'])}" aria-haspopup="dialog"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 10.5 6.8-4M8.6 13.5l6.8 4"/></svg></button>'''
    intro_html = f'<div class="selection-intro">{paras(intro)}</div>' if intro.strip() else ''
    heading = 'selection-heading selection-heading-title-only' if not intro.strip() else 'selection-heading'
    body = f'''<article data-selection-slug="{E(data['slug'])}"><header class="{heading}"><div class="selection-title"><h1>{E(title)}</h1>{share}</div>{intro_html}</header><div class="selection-grid">{''.join(rows)}</div></article>
<dialog class="selection-share" aria-labelledby="selection-share-title"><header><h2 id="selection-share-title">{E(labels['share'])}</h2><button type="button" data-share-dismiss aria-label="{E(labels['close'])}">×</button></header><label for="selection-share-url">{E(labels['link'])}</label><input id="selection-share-url" readonly><button type="button" class="button" data-selection-copy>{E(labels['copy'])}</button><p data-share-result role="status"></p></dialog>
<dialog class="selection-viewer" aria-label="{E(labels['viewer'])}"><header><span data-title></span><button type="button" data-dismiss aria-label="{E(labels['close'])}">×</button></header><img src="{E(h(post['cover']))}" alt=""><footer><a>{E(labels['card'])}</a><span data-position aria-live="polite"></span><div><button type="button" data-move="-1">{E(labels['prev'])}</button><button type="button" data-move="1">{E(labels['next'])}</button></div></footer></dialog>'''
    extra = f'<link rel="stylesheet" href="{h("assets/selections.css")}"><script src="{h("assets/selections.js")}" defer></script>'
    shell(path, lang, title, intro, body, f'{"en" if lang == "ru" else "ru"}/journal/{data["slug"]}/index.html', post['cover'], extra_head=extra)
