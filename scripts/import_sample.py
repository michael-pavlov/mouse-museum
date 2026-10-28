#!/usr/bin/env python3
"""Import a reviewed selection from cached Collectionerus records and photos.

Usage: python3 scripts/import_sample.py records.json /path/to/photo-cache
Photo cache names: mouse-photo-{sourceId}-{zero-based-photo-index}.bin.
Requires Pillow for image conversion; journal builds use Python-Markdown.
"""
import argparse
import json
import re
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('records', type=Path)
p.add_argument('photos', type=Path)
args = p.parse_args()
existing = [json.loads(f.read_text()) for f in (ROOT/'content/mice').glob('*.json')]
known = {d['source'] for d in existing}
order = max(d['order'] for d in existing) + 1
tracking = {
 'оптический через коврик': ('optical-pad', 'Optical · special pad'),
 'на потенциометрах': ('potentiometer', 'Potentiometers'),
 'оптико-механический (классика)': ('ball', 'Optomechanical ball'),
 'оптико-механический (особенный)': ('ball-special', 'Optomechanical · special mechanism'),
 'на дискретных датчиках (hawley)': ('discrete-hawley', 'Discrete sensors (Hawley)'),
 'на датчиках с осевым наклоном (hawley)': ('hawley-tilt', 'Axial tilt sensors (Hawley)'),
}
count = 0
for record in json.loads(args.records.read_text()):
 ident = record['sourceId']
 source = f'https://collectionerus.ru/collections/old-mice/{ident}/'
 if source in known:
  continue
 title = record['title']
 slug = re.sub('[^a-z0-9]+', '-', title.lower()).strip('-') + f'-{ident}'
 props = record['properties']
 year = int(props['Год'])
 tech = props.get('Способ позиционирования', '')
 key, english = tracking[tech.lower()] if tech else ('unknown','Not recorded')
 folder = ROOT/'assets/photos'/slug
 folder.mkdir(parents=True, exist_ok=True)
 photos = []
 for i, url in enumerate(record['photos']):
  with Image.open(args.photos/f'mouse-photo-{ident}-{i}.bin') as original:
   image = ImageOps.exif_transpose(original).convert('RGB')
   image.thumbnail((1600,1600), Image.Resampling.LANCZOS)
   filename = f'assets/photos/{slug}/{i+1:02}.webp'
   image.save(ROOT/filename, 'WEBP', quality=80, method=6)
   if i == 0:
    image.thumbnail((600,600), Image.Resampling.LANCZOS)
    image.save(folder/'thumb.webp', 'WEBP', quality=82)
  photos.append({'file': filename, 'source': 'https://collectionerus.ru'+url})
 assert photos, title
 brand = props.get('Производитель') or 'Unknown'
 # Storage locations and exchange inventory stay out of the public import.
 public_props = {k:v for k,v in props.items() if k not in ('Где посмотреть','Обменный фонд')}
 data = dict(id=f'MP-{ident:04}', slug=slug, title={'en':title,'ru':record.get('titleRu',title)}, source=source,
  sourceProperties=public_props, photos=photos, thumbnail=f'assets/photos/{slug}/thumb.webp',
  order=order, manufacturer={'en':brand,'ru':brand if brand!='Unknown' else 'Не указан'}, brand=brand, year=year,
  tracking={'key':key,'en':english,'ru':tech or 'Не указана'}, interface=props.get('Интерфейс') or None,
  soviet=props.get('СССР','').lower()=='да', features={'en':'','ru':props.get('Особенности','')},
  description={'en':'','ru':''}, notes={'en':'','ru':''})
 (ROOT/'content/mice'/f'{slug}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 known.add(source)
 order += 1
 count += 1
print(f'Imported {count} new specimens.')
