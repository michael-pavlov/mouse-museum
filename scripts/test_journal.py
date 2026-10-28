"""Check reciprocal links, source preservation and safe inline rendering."""
import json
import unittest
from pathlib import Path
from journal import Journal

ROOT = Path(__file__).resolve().parents[1]

class JournalTests(unittest.TestCase):
    def setUp(self):
        items = [json.loads(p.read_text()) for p in (ROOT/'content/mice').glob('*.json')]
        self.journal = Journal(ROOT, items)

    def test_links_in_both_directions_and_languages(self):
        for post in self.journal.posts:
            for language in ('en', 'ru'):
                path = self.journal.post_path(post, language)
                article = (ROOT/'dist'/path).read_text()
                self.assertIn(post['source'], article)
                self.assertIn(post['date'], article)
                self.assertNotIn('onclick=', article)
                for slug in post['relatedItems']:
                    self.assertIn(f'mice/{slug}/index.html', article)
                    item_page = (ROOT/f'dist/{language}/mice/{slug}/index.html').read_text()
                    self.assertIn(f'journal/{post["slug"]}/index.html', item_page)

    def test_local_image_assets(self):
        for language in ('en', 'ru'):
            for file in (ROOT/'dist'/language/'journal').rglob('index.html'):
                self.assertNotIn('src="https://', file.read_text())

    def render_text(self, text):
        post = next(p for p in self.journal.posts if p['slug']=='mindset-mouse')
        key = (post['slug'],'ru')
        source,_ = self.journal.markdown[key]
        self.journal.markdown[key] = (source,text)
        return self.journal.render_markdown(post,'ru','ru/journal/mindset-mouse/index.html')

    def test_markdown_sanitizer_and_local_inline_links(self):
        result = self.render_text('<a href="javascript:alert(1)" onclick="bad()">bad</a><img src="../../../assets/posts/mindset-mouse/01.webp" onerror="bad()"><strong>safe &amp; sound</strong>')
        self.assertNotIn('javascript:', result)
        self.assertNotIn('onclick', result)
        self.assertNotIn('onerror', result)
        self.assertIn('<strong>safe &amp; sound</strong>', result)
        result = self.render_text('[Green Eye](https://collectionerus.ru/collections/old-mice/3/)')
        self.assertIn('../../mice/microsoft-green-eye/index.html',result)

    def test_photo_stays_between_paragraphs_with_caption(self):
        result = self.render_text('Before the photo.\n\n![Mechanism](../../../assets/posts/mindset-mouse/02.webp "Inside the mouse")\n\nAfter the photo.')
        self.assertLess(result.index('Before the photo.'), result.index('<img'))
        self.assertLess(result.index('<img'), result.index('After the photo.'))
        self.assertIn('photo-caption', result)
        self.assertIn('Inside the mouse', result)
        self.assertIn('../../../assets/posts/mindset-mouse/02.webp',result)

    def test_markdown_formatting_and_single_page_heading(self):
        result = self.render_text('# A heading\n\n**Bold** and *italic*.\n\n- One\n- Two\n\n> A quote')
        for tag in ('<h2>','<strong>','<em>','<ul>','<li>','<blockquote>'):
            self.assertIn(tag,result)
        self.assertNotIn('<h1>',result)

    def test_broken_image_fails_build_instead_of_disappearing(self):
        with self.assertRaisesRegex(AssertionError,'Missing Markdown file reference'):
            self.render_text('![Missing](../../../assets/posts/missing-photo.webp)')

    def test_unrelated_objects_have_no_backlinks(self):
        item = self.journal.items['apple-macintosh-m0100']
        self.assertEqual(self.journal.mentions(item,'ru','ru/mice/apple-macintosh-m0100/index.html'),'')

if __name__ == '__main__':
    unittest.main()
