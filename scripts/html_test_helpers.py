"""HTML assertions shared by page tests."""
from html.parser import HTMLParser
from urllib.parse import urlsplit


class ImageSources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.noscript_depth = 0
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == 'noscript':
            self.noscript_depth += 1
        if tag == 'img':
            self.sources.append((dict(attrs).get('src', ''), self.noscript_depth > 0))

    def handle_endtag(self, tag):
        if tag == 'noscript':
            self.noscript_depth = max(0, self.noscript_depth - 1)


def assert_local_images(test, markup):
    images = ImageSources()
    images.feed(markup)
    for src, in_noscript in images.sources:
        if in_noscript and src == 'https://mc.yandex.ru/watch/113889111':
            continue
        url = urlsplit(src)
        test.assertTrue(src, 'Image is missing its source')
        test.assertFalse(url.scheme or url.netloc, f'External image: {src}')
