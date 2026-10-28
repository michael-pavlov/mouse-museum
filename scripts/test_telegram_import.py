"""Audit completeness of the imported public archive and offline media."""
import hashlib
import json
import re
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from journal import Journal

ROOT = Path(__file__).resolve().parents[1]


class TelegramArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = json.loads((ROOT/'data/source/telegram/posts.json').read_text())
        cls.excluded = set(json.loads((ROOT/'content/journal-exclusions.json').read_text())['sources'])
        cls.archived_posts = {post['source']:post for path in (ROOT/'content/posts').glob('*.json') for post in [json.loads(path.read_text())]}
        cls.journal = Journal(ROOT, [json.loads(p.read_text()) for p in (ROOT/'content/mice').glob('*.json')])
        cls.posts = {post['source']:post for post in cls.journal.posts}

    def test_complete_feed_has_one_article_per_authored_record(self):
        self.assertIn('https://t.me/old_mice_and_hw/1', [p['source'] for p in self.archive])
        authored = {p['source'] for p in self.archive if not p['source'].endswith('/1')}
        self.assertEqual(authored - self.excluded, set(self.posts))
        for source in self.excluded:
            slug = self.archived_posts[source]['slug']
            for language in ('en','ru'):
                self.assertFalse((ROOT/f'dist/{language}/journal/{slug}/index.html').exists())
                self.assertNotIn(f'{slug}/index.html', (ROOT/f'dist/{language}/journal/index.html').read_text())
        for record in self.archive:
            if record['source'] in self.posts:
                self.assertEqual(record['date'], self.posts[record['source']]['date'])

    def test_original_downloads_match_manifest_and_decode(self):
        manifest = json.loads((ROOT/'data/source/telegram/media-manifest.json').read_text())
        expected = sum(len(p['photos']) + len(p['videos']) for p in self.archive)
        self.assertEqual(len(manifest), expected)
        for entry in manifest:
            file = ROOT/entry['file']
            self.assertEqual(file.stat().st_size, entry['bytes'])
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), entry['sha256'])
            if file.suffix == '.jpg':
                with Image.open(file) as image:
                    image.load()
                    self.assertGreater(min(image.size), 0)
            else:
                self.assertIn(b'ftyp', file.read_bytes()[:32])

    def test_each_new_album_preserves_order_and_originals(self):
        for record in self.archive:
            post = self.posts.get(record['source'])
            if not post or not post['slug'].startswith('telegram-'):
                continue
            self.assertEqual([p['source'] for p in post['photos']], record['photos'])
            for language in ('ru', 'en'):
                page = BeautifulSoup((ROOT/'dist'/self.journal.post_path(post,language)).read_text(), 'html.parser')
                photos = page.select('.post-prose .article-photo')
                self.assertEqual(len(photos), len(record['photos']))
                for link, photo in zip(photos, post['photos']):
                    self.assertTrue(link['href'].endswith(photo['original']))
                visible = page.select_one('.post-prose').get_text(' ', strip=True)
                if language == 'en':
                    self.assertIsNone(re.search('[А-Яа-яЁё]', visible), post['slug'])

    def test_videos_quiz_and_unavailable_media_are_explicit(self):
        self.assertEqual(sum(len(p.get('videos', [])) for p in self.posts.values()), 3)
        for language in ('ru', 'en'):
            page = (ROOT/f'dist/{language}/journal/telegram-115/index.html').read_text()
            self.assertIn('<video controls playsinline preload="metadata"', page)
            self.assertIn('video-01.mp4', page)
            missing = (ROOT/f'dist/{language}/journal/telegram-110/index.html').read_text()
            self.assertIn(self.posts['https://t.me/old_mice_and_hw/110']['mediaNote'][language], missing)

    def test_cross_post_links_stay_in_the_selected_language(self):
        post = self.posts['https://t.me/old_mice_and_hw/134']
        for language in ('en', 'ru'):
            page = (ROOT/'dist'/self.journal.post_path(post, language)).read_text()
            self.assertIn('../telegram-131/index.html', page)


if __name__ == '__main__':
    unittest.main()
