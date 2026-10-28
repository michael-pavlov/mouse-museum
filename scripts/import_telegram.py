#!/usr/bin/env python3
"""Import the saved public Telegram archive, preserving existing article URLs.

Offline and repeatable: requires data/source/telegram/posts.json, reviewed
translations.md and downloaded assets/posts/telegram-*/ files. Does not use keys.
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup, NavigableString
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/source/telegram'


def markdown_node(node):
    if isinstance(node, NavigableString):
        return str(node)
    if node.name == 'br':
        return '\n'
    text = ''.join(markdown_node(child) for child in node.children)
    stripped = text.strip()
    if node.name == 'a':
        href = html.unescape(node.get('href', ''))
        if href.startswith('?'):
            href = 'https://t.me/s/old_mice_and_hw' + href
        return f'[{stripped}]({href})' + ('\n' if text.endswith('\n') else '')
    if node.name in ('b', 'strong', 'i', 'em'):
        marker = '**' if node.name in ('b', 'strong') else '*'
        return (marker + stripped + marker if stripped else '') + ('\n' if text.endswith('\n') else '')
    return text


def plain(text):
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return re.sub(r'[*_`#]', '', text).strip()


def excerpt(text):
    paragraphs = [plain(p) for p in text.split('\n\n') if plain(p)]
    # A short opening line is usually the original title.
    value = next((p for p in paragraphs if len(p) > 65), paragraphs[0] if paragraphs else '')
    value = ' '.join(value.split())
    if len(value) > 175:
        value = value[:172].rsplit(' ', 1)[0].rstrip('.,;:') + '…'
    return value


def insert_photos(text, photos, title, language):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = ['Фотография из канала. В оригинале опубликована без подписи.' if language == 'ru' else 'A photograph from the channel, originally published without a caption.']
    # Keep source paragraph order and album order; distribute photos in the prose.
    slots = {}
    for i, photo in enumerate(photos):
        slot = min(len(paragraphs) - 1, (i * len(paragraphs)) // max(1, len(photos)))
        alt = f'{title} — фото {i+1}' if language == 'ru' else f'{title} — photo {i+1}'
        slots.setdefault(slot, []).append(f'![{alt}](../../../{photo["file"]})')
    return '\n\n'.join(part for i, p in enumerate(paragraphs) for part in [p, *slots.get(i, [])]) + '\n'


def main():
    archive = json.loads((SOURCE/'posts.json').read_text())
    exclusions = ROOT/'content/journal-exclusions.json'
    excluded = set(json.loads(exclusions.read_text())['sources']) if exclusions.exists() else set()
    excerpts = json.loads((SOURCE/'excerpts.json').read_text())
    translations = {}
    for block in re.split(r'^### ', (SOURCE/'translations.md').read_text(), flags=re.M)[1:]:
        header, body = block.split('\n', 1)
        id, ru_title, en_title = [part.strip() for part in header.split('|')]
        translations[id] = {'title': {'ru': ru_title, 'en': en_title}, 'en': body.strip()}
    existing = {p['source']: (path, p) for path in (ROOT/'content/posts').glob('*.json') for p in [json.loads(path.read_text())]}
    mice = [json.loads(p.read_text()) for p in (ROOT/'content/mice').glob('*.json')]
    by_source = {p['source'].rstrip('/'): p['slug'] for p in mice}
    event_dates = {'37':'2023-06-24', '207':'2025-09-27', '208':'2025-09-27', '217':'2025-09-28', '247':'2026-08-08', '249':'2026-09-05'}
    report = {'channel':'https://t.me/old_mice_and_hw', 'publicRecords':len(archive), 'posts':[], 'excluded':[], 'limits':[
        'Only the public channel feed is archived. Deleted or non-public messages cannot be recovered.',
        'Comments and attachments in the discussion group are outside the public channel feed; continuations mentioned in posts 54 and 134 are not included.',
        'Quiz 173 is preserved as a static question with options; it does not accept votes.',
        'Post 110 contains a video unavailable as a downloadable file in the public feed. A source link is retained.',
        'Publication dates and historical claims are preserved as authored; this is a translation, not a separate historical fact-check.'
    ]}
    for source in archive:
        id = source['source'].rsplit('/',1)[-1]
        if source['source'] in excluded:
            report['excluded'].append({'id':int(id), 'reason':'Excluded from the journal by the owner.'})
            continue
        if id == '1':
            report['excluded'].append({'id':1, 'reason':'Telegram channel-created service message; not an authored publication.'})
            continue
        if source['source'] in existing and not existing[source['source']][1]['slug'].startswith('telegram-'):
            path, post = existing[source['source']]
            # Keep editorial structure, text, photos and public URLs already in use.
            report['posts'].append({'id':int(id), 'slug':post['slug'], 'status':'existing', 'photos':len(post['photos'])})
            continue
        assert id in translations, f'Missing English translation for {id}'
        translation = translations[id]
        slug = f'telegram-{id}'
        path = ROOT/f'content/posts/{slug}.json'
        text = markdown_node(BeautifulSoup(source['html'], 'html.parser')).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        first, separator, rest = text.partition('\n')
        if separator and rest.strip() and (plain(first).casefold() == translation['title']['ru'].casefold() or ('collectionerus.ru/collections/' in first and len(plain(first)) < 90)):
            text = rest.strip()
        if source.get('poll'):
            poll = source['poll']
            text = poll['question'] + '\n\n' + '\n'.join('- ' + option for option in poll['options']) + '\n\nАрхив вопроса и вариантов ответа. Оригинальный опрос находится в Telegram.'
        if not text:
            text = 'Фотография из канала. В оригинале опубликована без подписи.'
        photos = []
        for i, url in enumerate(source['photos'], 1):
            file = f'assets/posts/{slug}/{i:02}.webp'
            with Image.open(ROOT/file) as image:
                width, height = image.size
            photos.append({'file':file, 'original':f'assets/posts/{slug}/{i:02}.jpg', 'source':url, 'width':width, 'height':height})
        related = []
        source_urls = [html.unescape(a['href']) for a in BeautifulSoup(source['html'], 'html.parser').select('a[href]')]
        for url in source_urls:
            item = by_source.get(url.rstrip('/'))
            if item and item not in related:
                related.append(item)
        for item in mice:
            channel_posts = item.get('channelPost', [])
            if isinstance(channel_posts, str):
                channel_posts = [channel_posts]
            if source['source'] in channel_posts and item['slug'] not in related:
                related.insert(0, item['slug'])
        cover = photos[0]['file'] if photos else 'assets/mouse-museum-logo.png'
        # Illustration of the quiz and its adjacent invitation, not an invented cover.
        if id == '173':
            cover = 'assets/posts/telegram-172/01.webp'
        if id == '207':
            cover = 'assets/posts/telegram-208/01.webp'
        body_files = {lang:f'content/posts/{slug}/{lang}.md' for lang in ('ru','en')}
        post = {'id':'telegram-'+id, 'slug':slug, 'title':translation['title'], 'date':source['date'], 'source':source['source'],
                'excerpt':excerpts[id], 'photos':photos, 'cover':cover,
                'relatedItems':related, 'category':'exhibitions' if id in event_dates else 'stories',
                'translationNote':{'ru':'', 'en':'Translated from the original Russian post.'}, 'bodyFiles':body_files}
        if id in event_dates:
            post['eventDate'] = event_dates[id]
        videos = []
        for i, url in enumerate(source.get('videos', []), 1):
            file = f'assets/posts/{slug}/video-{i:02}.mp4'
            assert (ROOT/file).is_file()
            videos.append({'file':file, 'source':url})
        if videos:
            post['videos'] = videos
        if source['video'] and not videos:
            post['mediaNote'] = {'ru':'Видео к этой записи доступно в оригинальной публикации Telegram.', 'en':'The video accompanying this post is available in the original Telegram publication.'}
        if id in ('54', '134', '201'):
            post['archiveNote'] = {'ru':'В оригинале упоминаются материалы в комментариях. Здесь сохранена публикация канала; обсуждение смотрите в Telegram.', 'en':'The original refers to material in the comments. This archive preserves the channel post; the discussion remains on Telegram.'}
        # Retain any original external references absent from the translation.
        references = []
        for url in dict.fromkeys(source_urls):
            if urlsplit(url).scheme not in ('http', 'https') or url in translation['en']:
                continue
            references.append({'url':url, 'label':{'ru':f'Ссылка из оригинала {len(references)+1}', 'en':f'Original reference {len(references)+1}'}})
        if references:
            post['references'] = references
        for lang, body in [('ru',text), ('en',translation['en'])]:
            file = ROOT/body_files[lang]
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(insert_photos(body, photos, translation['title'][lang], lang))
        path.write_text(json.dumps(post, ensure_ascii=False, indent=2)+'\n')
        report['posts'].append({'id':int(id), 'slug':slug, 'status':'imported', 'photos':len(photos), 'videos':len(videos), 'relatedItems':related})
    report['journalPosts'] = len(report['posts'])
    (ROOT/'reports/telegram-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'Journal: {report["journalPosts"]} posts; service records excluded: {len(report["excluded"])}')


if __name__ == '__main__':
    main()
