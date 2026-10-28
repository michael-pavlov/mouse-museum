#!/usr/bin/env python3
"""Import cached public wanted/exchange selections. Requires Pillow only at import.

python3 scripts/import_wanted.py wanted-album.json exchange-records.json /path/to/cache
Cache files: mouse-wanted-{ibb-id}.bin and mouse-exchange-photo-{sourceId}.bin.
Album metadata comes from public ImgBB data-object entries; exchange records must
be verified against each item's explicit Обменный фонд property before importing.
"""
import argparse
import json
import re
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('album', type=Path)
p.add_argument('exchange', type=Path)
p.add_argument('cache', type=Path)
args = p.parse_args()

def save_images(raw, folder):
    folder.mkdir(parents=True, exist_ok=True)
    with Image.open(raw) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
        image.thumbnail((1400,1400), Image.Resampling.LANCZOS)
        image.save(folder/'photo.webp', 'WEBP', quality=86)
        image.thumbnail((640,640), Image.Resampling.LANCZOS)
        image.save(folder/'thumb.webp', 'WEBP', quality=84)
    return {'image':(folder/'photo.webp').relative_to(ROOT).as_posix(),
            'thumbnail':(folder/'thumb.webp').relative_to(ROOT).as_posix()}

for order, entry in enumerate(json.loads(args.album.read_text()),1):
    ident = entry['id_encoded']
    slug = 'w-'+ident.lower()
    dest = ROOT/'content/wanted'/f'{slug}.json'
    # Keep later owner edits to labels and availability on a repeated import.
    if dest.exists():
        continue
    data = {'id':slug,'reference':f'W-{order:02}','order':order,'title':{'en':'','ru':''},
            'source':entry['url_viewer'],'photoSource':entry['image']['url'],
            'sourceFilename':entry['filename'],'status':'wanted'}
    data.update(save_images(args.cache/f'mouse-wanted-{ident}.bin', ROOT/'assets/wanted'/slug))
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

local_items = {json.loads(f.read_text())['source']:json.loads(f.read_text())['slug'] for f in (ROOT/'content/mice').glob('*.json')}
for order, entry in enumerate(json.loads(args.exchange.read_text()),1):
    assert 'есть' in entry['stock'].lower()
    slug = f'exchange-{entry["sourceId"]}'
    dest = ROOT/'content/exchange'/f'{slug}.json'
    if dest.exists():
        continue
    count = re.search(r'\d+',entry['stock'])
    assert entry['source'] in local_items, 'Import the specimen into the catalogue first: '+entry['source']
    data = {'id':slug,'order':order,'source':entry['source'],
            'sourceStock':entry['stock'],'quantity':int(count[0]) if count else None,
            'catalogueSlug':local_items[entry['source']],'status':'available'}
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print('Wanted and exchange selections imported.')
