"""Optional specimen fields, legacy compatibility and reference rendering."""
import json
import unittest
from pathlib import Path
from specimen_content import channel_posts,viewing_location,description_html,resources_html,validate_extras

ROOT=Path(__file__).resolve().parents[1]

class SpecimenContentTests(unittest.TestCase):
    def test_empty_optional_blocks_are_absent(self):
        self.assertEqual(description_html({},'ru'),'')
        self.assertEqual(resources_html({},'en'),'')
        self.assertEqual(viewing_location({},'ru'),'')

    def test_legacy_telegram_field_ignores_abbreviated_duplicate_labels(self):
        data={'sourceProperties':{'Пост в канале':'t.me/old_mice_and_hw/68 t.me/.../68 t.me/... t.me'}}
        self.assertEqual(channel_posts(data),['https://t.me/old_mice_and_hw/68'])
        self.assertEqual(resources_html(data,'ru').count('href='),1)
        data['channelPost']=''
        self.assertEqual(channel_posts(data),[])

    def test_explicit_telegram_replaces_legacy_and_deduplicates(self):
        data={'channelPost':['https://t.me/old_mice_and_hw/68']*2,'sourceProperties':{'Пост в канале':'t.me/old_mice_and_hw/54'}}
        self.assertEqual(channel_posts(data),['https://t.me/old_mice_and_hw/68'])

    def test_plain_text_paragraphs_are_preserved_and_escaped(self):
        result=description_html({'description':{'ru':'Первый абзац.\nВторая строка.\n\n<script>Текст</script>'}},'ru')
        self.assertEqual(result.count('<p>'),2)
        self.assertIn('<br>',result)
        self.assertNotIn('<script>',result)
        self.assertIn('&lt;script&gt;',result)

    def test_location_fallback_and_explicit_empty(self):
        data={'sourceProperties':{'Где посмотреть':'Краснохолмская'}}
        self.assertEqual(viewing_location(data,'ru'),'Краснохолмская')
        self.assertEqual(viewing_location(data,'en'),'Krasnokholmskaya Gallery')
        data['whereToSee']={'ru':'','en':''}
        self.assertEqual(viewing_location(data,'ru'),'')

    def test_invalid_reference_fails_validation(self):
        with self.assertRaises(AssertionError):
            validate_extras({'externalLinks':[{'url':'javascript:alert(1)','title':{'en':'x','ru':'x'}}]})
        with self.assertRaises(AssertionError):
            validate_extras({'channelPost':'https://example.com/68'})

    def test_original_record_joins_references_without_duplicates(self):
        url='https://collectionerus.ru/collections/old-mice/3/'
        item={'source':url}
        result=resources_html(item,'ru')
        self.assertIn('Запись на Коллекционерусе',result)
        self.assertEqual(result.count('href='),1)
        item['externalLinks']=[{'url':url,'title':{'en':'Collectionerus','ru':'Коллекционерус'}}]
        self.assertEqual(resources_html(item,'ru').count('href='),1)

    def test_imported_examples_have_their_actual_materials(self):
        penny=json.loads((ROOT/'content/mice/penny-giles-m3-100-for-acorn-a500-191.json').read_text())
        tandy=json.loads((ROOT/'content/mice/tandy-color-mouse.json').read_text())
        self.assertEqual(len(penny['externalLinks']),1)
        self.assertEqual(len(tandy['externalLinks']),4)
        for language in ('en','ru'):
            html=(ROOT/f'dist/{language}/mice/{penny["slug"]}/index.html').read_text()
            self.assertIn('https://t.me/old_mice_and_hw/68',html)
            self.assertIn('Sinclair QL',html)
            for item in (penny,tandy):
                result=resources_html(item,language)
                self.assertEqual(result.count('target="_blank"'),len(item['externalLinks'])+len(channel_posts(item))+1)

if __name__=='__main__':
    unittest.main()
