"""Audit imported records against stored source snapshots and original files."""
import hashlib
import json
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

class FullSourceSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items=[json.loads(p.read_text()) for p in (ROOT/'content/mice').glob('*.json')]

    def test_every_specimen_has_complete_matching_source_data(self):
        for item in self.items:
            ident=item['source'].rstrip('/').rsplit('/',1)[-1]
            source=json.loads((ROOT/f'data/source/collectionerus/{ident}.json').read_text())
            self.assertEqual(item['sourceProperties'],source['properties'],item['slug'])
            self.assertEqual(len(item['photos']),len(source['photos']),item['slug'])
            self.assertEqual(item['sourceSync']['sourcePhotoCount'],len(item['photos']))
            self.assertEqual([p['originalSource'] for p in item['photos']],[p['originalSource'] for p in source['photos']])
            self.assertEqual({link['url'] for link in item['externalLinks']},{link['url'] for link in source['externalLinks']})
            self.assertEqual(item['description']['ru'],source['descriptionText'])
            self.assertEqual(item['year'],int(source['properties']['Год']) if source['properties'].get('Год') else None)
            self.assertEqual(item['whereToSee']['ru'],source['properties'].get('Где посмотреть',''))
            self.assertEqual(item['boardManufacturer']['ru'],source['properties'].get('Производитель платы',''))

    def test_originals_are_valid_and_unchanged(self):
        for item in self.items:
            for photo in item['photos']:
                original=ROOT/photo['original']
                self.assertEqual(original.stat().st_size,photo['originalBytes'])
                self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),photo['sha256'])
                with Image.open(original) as image:
                    self.assertEqual(image.size,(photo['originalWidth'],photo['originalHeight']))
                    image.load()
                for key in ('file','thumbnail'):
                    with Image.open(ROOT/photo[key]) as image:
                        image.load()
                        self.assertEqual(image.format,'WEBP')

    def test_generated_pages_have_thumbnails_without_original_links(self):
        for item in self.items:
            for language in ('en','ru'):
                page=(ROOT/f'dist/{language}/mice/{item["slug"]}/index.html').read_text()
                self.assertNotIn('data-original="',page)
                self.assertIn(f'/ {len(item["photos"]):02}',page)
                self.assertNotIn('id="original-photo"',page)
                for photo in item['photos']:
                    self.assertNotIn(photo['original'],page)
                    self.assertIn(photo['thumbnail'],page)

    def test_complete_discovery_index_matches_local_catalogue(self):
        path=ROOT/'data/source/catalogue-index.json'
        if not path.exists():
            self.skipTest('No full discovery index for a sample-only catalogue')
        index=json.loads(path.read_text())
        self.assertEqual(index['count'],len(self.items))
        self.assertEqual({row['source'] for row in index['entries']},{item['source'] for item in self.items})
        self.assertEqual(len({item['slug'] for item in self.items}),len(self.items))

    def test_report_totals_agree(self):
        report=json.loads((ROOT/'reports/collectionerus-sync.json').read_text())
        self.assertEqual(report['specimens'],len(self.items))
        self.assertEqual(report['photos'],sum(len(item['photos']) for item in self.items))
        self.assertEqual(report.get('availableOriginals',report['photos']),sum(photo.get('originalAvailable',True) for item in self.items for photo in item['photos']))
        self.assertEqual(len(report.get('unavailableOriginals',[])),sum(not photo.get('originalAvailable',True) for item in self.items for photo in item['photos']))
        self.assertEqual(report['originalBytes'],sum(p['originalBytes'] for item in self.items for p in item['photos']))

if __name__=='__main__':
    unittest.main()
