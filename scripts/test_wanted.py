"""Validate contact drafts, exchange provenance and isolation from the collection."""
import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from wanted import Wanted, EMAIL

ROOT=Path(__file__).resolve().parents[1]

class WantedTests(unittest.TestCase):
    def setUp(self):
        self.items=[json.loads(p.read_text()) for p in (ROOT/'content/mice').glob('*.json')]
        self.wanted=Wanted(ROOT,self.items)

    def test_imported_exchange_has_explicit_source_evidence(self):
        self.assertEqual(len(self.wanted.exchange),15)
        for entry in self.wanted.exchange:
            self.assertIn('есть',entry['sourceStock'])
            self.assertGreater(entry['quantity'],0)
            self.assertTrue(entry['source'].startswith('https://collectionerus.ru/collections/old-mice/'))

    def test_drafts_identify_each_item_without_sending(self):
        for language in ('en','ru'):
            for exchange in (False,True):
                entries=self.wanted.exchange if exchange else self.wanted.wanted
                for entry in entries:
                    parts=urlsplit(self.wanted.mailto(entry,language,exchange))
                    self.assertEqual(parts.scheme,'mailto')
                    self.assertEqual(parts.path,EMAIL)
                    fields=parse_qs(parts.query)
                    name=entry['title'][language] or entry['reference']
                    self.assertIn(name,fields['subject'][0])
                    self.assertIn(entry['source'],fields['body'][0])
                    self.assertIn('\n',fields['body'][0])

    def test_public_site_drafts_have_stable_local_anchors(self):
        wanted=Wanted(ROOT,self.items,'https://example.com/museum')
        entry=wanted.wanted[0]
        body=parse_qs(urlsplit(wanted.mailto(entry,'ru')).query)['body'][0]
        self.assertIn(f'https://example.com/museum/ru/wanted/#{entry["id"]}',body)

    def test_pages_images_tabs_and_mail_links(self):
        for language in ('en','ru'):
            for exchange in (False,True):
                page=(ROOT/'dist'/self.wanted.page_path(language,exchange)).read_text()
                entries=self.wanted.exchange if exchange else self.wanted.wanted
                for entry in entries:
                    self.assertIn(f'id="{entry["id"]}"',page)
                    self.assertIn(entry['thumbnail'],page)
                self.assertEqual(page.count('class="wanted-card'),len(entries))
                self.assertIn('mailto:'+EMAIL,page)
                self.assertNotIn('src="https://',page)
                self.assertIn('aria-current="page"',page)

    def test_exchange_backlinks_only_where_specimen_is_known(self):
        for entry in self.wanted.exchange:
            slug=entry.get('catalogueSlug')
            if slug:
                for language in ('en','ru'):
                    page=(ROOT/f'dist/{language}/mice/{slug}/index.html').read_text()
                    self.assertIn('exchange/index.html#'+entry['id'],page)

    def test_exchange_uses_catalogue_data_and_opens_specimen(self):
        by_slug={item['slug']:item for item in self.items}
        for entry in self.wanted.exchange:
            item=by_slug[entry['catalogueSlug']]
            self.assertEqual(entry['title'],item['title'])
            self.assertEqual(entry['thumbnail'],item['thumbnail'])
            for language in ('en','ru'):
                page=(ROOT/'dist'/self.wanted.page_path(language,True)).read_text()
                self.assertIn('mice/'+item['slug']+'/index.html',page)
                self.assertNotIn('class="wanted-photo"',page)
                self.assertIn(str(entry['quantity'])+' '+('шт.' if language=='ru' else 'available'),page)

    def test_wanted_does_not_change_catalogue_count(self):
        page=(ROOT/'dist/en/index.html').read_text()
        self.assertIn(f'Catalogue ({len(self.items)} items)',page)
        self.assertEqual(page.count('class="card"'),len(self.items))

if __name__=='__main__':
    unittest.main()
