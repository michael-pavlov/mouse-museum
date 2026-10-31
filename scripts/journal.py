"""Static bilingual journal with explicit specimen links and generated backlinks."""
import html
import json
import posixpath
import re
from datetime import datetime, date
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

import markdown


def esc(value):
    return html.escape(str(value), quote=True)


def tr(en, ru, language):
    return ru if language == 'ru' else en


def relative(path, target):
    return posixpath.relpath(target, posixpath.dirname(path) or '.')


class MarkdownHTML(HTMLParser):
    """Render safe Markdown HTML and resolve file paths from the source .md file."""
    tags = {'p','h1','h2','h3','h4','h5','h6','strong','em','b','i','ul','ol','li',
            'blockquote','pre','code','br','hr','a','img','del'}
    void = {'br','hr','img'}

    def __init__(self, root, source_file, page_path, rewrite, dimensions, originals=None):
        super().__init__(convert_charrefs=True)
        self.root = root.resolve()
        self.source_file = source_file
        self.page_path = page_path
        self.rewrite = rewrite
        self.dimensions = dimensions
        self.originals = originals or {}
        self.output = []
        self.stack = []

    def local_file(self, url, image=False):
        parts = urlsplit(url)
        assert not parts.scheme and not parts.netloc, 'Article photos must be local files'
        raw = unquote(parts.path)
        target = (self.root/raw.lstrip('/') if raw.startswith('/') else self.source_file.parent/raw).resolve()
        assert target.is_relative_to(self.root), f'Path outside project: {url}'
        assert target.is_file(), f'Missing Markdown file reference: {url}'
        if image:
            assert target.is_relative_to(self.root/'assets'), f'Photo outside assets: {url}'
        file = target.relative_to(self.root).as_posix()
        return relative(self.page_path, file), file

    def href(self, url):
        parts = urlsplit(url)
        if parts.scheme in ('http','https','mailto'):
            return self.rewrite(url)
        if parts.scheme or parts.netloc or not url:
            return None
        if not parts.path:
            return url
        path, _ = self.local_file(url)
        return path + ('#'+parts.fragment if parts.fragment else '')

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in self.tags:
            return
        emitted = 'h2' if tag == 'h1' else tag
        extra = ''
        if tag == 'a':
            url = self.href(attrs.get('href',''))
            if url is None:
                self.stack.append((tag, None))
                return
            extra = f' href="{esc(url)}"'
        elif tag == 'img':
            url, file = self.local_file(attrs.get('src',''), image=True)
            size = self.dimensions.get(file)
            dimensions = f' width="{size[0]}" height="{size[1]}"' if size else ''
            full = relative(self.page_path, self.originals[file]) if file in self.originals else url
            self.output.append(f'<a class="article-photo" href="{esc(full)}"><img src="{esc(url)}" alt="{esc(attrs.get("alt",""))}"{dimensions} loading="lazy"></a>')
            if attrs.get('title'):
                self.output.append(f'<span class="photo-caption">{esc(attrs["title"])}</span>')
            return
        elif tag == 'ol' and attrs.get('start','').isdigit():
            extra = f' start="{int(attrs["start"])}"'
        self.output.append(f'<{emitted}{extra}>')
        if tag not in self.void:
            self.stack.append((tag, emitted))

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1][0] == tag:
            _, emitted = self.stack.pop()
            if emitted:
                self.output.append(f'</{emitted}>')

    def handle_data(self, data):
        self.output.append(esc(data))

    def result(self):
        return ''.join(self.output) + ''.join(f'</{emitted}>' for _,emitted in reversed(self.stack) if emitted)


class Journal:
    def __init__(self, root, items):
        self.root = root
        self.markdown = {}
        self.items = {item['slug']: item for item in items}
        self.by_source = {item['source'].rstrip('/'): item for item in items}
        exclusions = root/'content/journal-exclusions.json'
        excluded = set(json.loads(exclusions.read_text())['sources']) if exclusions.exists() else set()
        self.posts = sorted(
            [post for p in (root/'content/posts').glob('*.json') for post in [json.loads(p.read_text())] if post['source'] not in excluded],
            key=lambda post: post['date'], reverse=True)
        self.by_post_source = {post['source'].rstrip('/'): post for post in self.posts}
        seen = set()
        for post in self.posts:
            assert re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', post['slug'])
            assert post['slug'] not in seen, 'Duplicate post slug'
            seen.add(post['slug'])
            datetime.fromisoformat(post['date'])
            for language in ('en', 'ru'):
                assert post['title'][language] and post['excerpt'][language]
                source = (root/post['bodyFiles'][language]).resolve()
                assert source.is_relative_to(root/'content/posts') and source.suffix == '.md' and source.is_file()
                text = source.read_text()
                assert text.strip(), f'Empty article: {source}'
                self.markdown[(post['slug'],language)] = (source,text)
            assert len(post['relatedItems']) == len(set(post['relatedItems']))
            for slug in post['relatedItems']:
                assert slug in self.items, f'Unknown specimen: {slug}'
            for file in [post['cover']] + [photo[key] for photo in post['photos'] for key in ('file', 'original') if photo.get(key)] + [video['file'] for video in post.get('videos', [])]:
                target = (root/file).resolve()
                assert target.is_relative_to(root/'assets') and target.is_file(), file

    @staticmethod
    def post_path(post, language):
        return f'{language}/journal/{post["slug"]}/index.html'

    @staticmethod
    def date_label(post, language):
        d = datetime.fromisoformat(post['date']).date()
        months = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')
        return f'{d.day} {months[d.month-1]} {d.year}' if language == 'ru' else d.strftime('%d %B %Y').lstrip('0')

    def render_markdown(self, post, language, path):
        source, text = self.markdown[(post['slug'],language)]
        def rewrite(url):
            linked_post = self.by_post_source.get(url.rstrip('/'))
            if linked_post:
                return relative(path, self.post_path(linked_post, language))
            item = self.by_source.get(url.rstrip('/'))
            return relative(path, f'{language}/mice/{item["slug"]}/index.html') if item else url
        dimensions = {photo['file']: (photo['width'],photo['height']) for photo in post['photos']}
        originals = {photo['file']: photo['original'] for photo in post['photos'] if photo.get('original')}
        parser = MarkdownHTML(self.root, source, path, rewrite, dimensions, originals)
        parser.feed(markdown.markdown(text))
        return parser.result()

    def reference_links(self, item, language, path):
        return [{'url': relative(path, self.post_path(post, language)),
                 'title': post['title'][language],
                 'source': tr('Museum journal', 'Журнал музея', language)}
                for post in self.posts if item['slug'] in post['relatedItems']]

    def mentions(self, item, language, path):
        posts = [post for post in self.posts if item['slug'] in post['relatedItems']]
        if not posts:
            return ''
        rows = ''.join(
            f'<a class="post-mention" href="{relative(path,self.post_path(post,language))}">'
            f'<time datetime="{esc(post["date"])}">{self.date_label(post,language)}</time>'
            f'<span>{esc(post["title"][language])}</span><span aria-hidden="true">→</span></a>'
            for post in posts)
        return f'<section class="post-mentions"><h2>{tr("Publications","Публикации",language)}</h2>{rows}</section>'

    def build(self, shell):
        for language in ('en', 'ru'):
            other = 'ru' if language == 'en' else 'en'
            path = f'{language}/journal/index.html'
            cards = []
            for post in self.posts:
                cards.append(f'''<article class="journal-card"><a href="{relative(path,self.post_path(post,language))}"><div class="journal-cover"><img src="{relative(path,post['cover'])}" alt="{esc(post['title'][language])}" loading="lazy"></div><div class="journal-meta"><time datetime="{esc(post['date'])}">{self.date_label(post,language)}</time><span>{tr('Exhibitions','Выставки',language) if post['category']=='exhibitions' else tr('Stories','Истории',language)}</span></div><h2>{esc(post['title'][language])}</h2><p>{esc(post['excerpt'][language])}</p><span class="journal-read">{tr('Read story','Читать',language)} →</span></a></article>''')
            body = f'''<section class="journal-heading"><h1>{tr('Journal','Журнал',language)}</h1><p>{tr('Stories behind the objects. Finds, mechanisms and life outside the display case.','Истории за экспонатами. Находки, механизмы и жизнь за пределами витрины.',language)}</p></section><div class="journal-grid">{''.join(cards)}</div>'''
            shell(path, language, tr('Journal','Журнал',language), tr('Stories, finds and exhibitions from Mouse Museum.','Истории, находки и выставки Mouse Museum.',language),body,f'{other}/journal/index.html',self.posts[0]['cover'] if self.posts else None)
            for post in self.posts:
                self.article(post, language, shell)

    def article(self, post, language, shell):
        path = self.post_path(post, language)
        h = lambda target: relative(path, target)
        title = esc(post['title'][language])
        paragraphs = self.render_markdown(post,language,path)
        for i, video in enumerate(post.get('videos', []), 1):
            url = esc(h(video['file']))
            label = tr(f'Video {i}', f'Видео {i}', language)
            paragraphs += f'<figure class="post-video"><video controls playsinline preload="metadata" src="{url}"><a href="{url}">{label}</a></video><figcaption><a href="{url}">{label} · {tr("Open video", "Открыть видео", language)}</a></figcaption></figure>'
        if post.get('mediaNote', {}).get(language):
            paragraphs += f'<p class="event-note">{esc(post["mediaNote"][language])}</p>'
        if post.get('archiveNote', {}).get(language):
            paragraphs += f'<p class="event-note">{esc(post["archiveNote"][language])}</p>'
        specimens = ''.join(f'<a class="journal-specimen" href="{h(f"{language}/mice/{slug}/index.html")}"><img src="{h(self.items[slug]["thumbnail"])}" alt="" loading="lazy"><span>{esc(self.items[slug]["title"][language])}</span></a>' for slug in post['relatedItems'])
        related = f'<section class="journal-related"><h2>{tr("Objects in this story","Экспонаты в публикации",language)}</h2><div class="journal-specimens">{specimens}</div></section>' if specimens else ''
        archived = bool(post.get('eventDate') and date.fromisoformat(post['eventDate']) < date.today())
        event_note = f'<p class="event-note">{tr("Past event · Original announcement preserved below.","Событие прошло · Ниже сохранён оригинальный анонс.",language)}</p>' if archived else ''
        note = post.get('translationNote',{}).get(language,'')
        reference = ''.join(f'<a href="{esc(ref["url"])}">{esc(ref["label"][language])}</a>' for ref in post.get('references',[]))

        body = f'''<nav class="breadcrumb" aria-label="{tr('Breadcrumb','Путь к странице',language)}"><a href="{h(language+'/journal/index.html')}">← {tr('Journal','Журнал',language)}</a></nav><article class="journal-post"><header class="post-heading"><time datetime="{esc(post['date'])}">{self.date_label(post,language)}</time><h1>{title}</h1><p class="post-deck">{esc(post['excerpt'][language])}</p></header><div class="post-prose">{event_note}{paragraphs}<div class="post-source">{f'<p>{esc(note)}</p>' if note else ''}<a href="{esc(post['source'])}">{tr('Original post on Telegram','Оригинал в Telegram',language)} ↗</a>{reference}</div></div>{related}</article>'''
        shell(path,language,post['title'][language],post['excerpt'][language],body,self.post_path(post,'ru' if language=='en' else 'en'),post['cover'])
