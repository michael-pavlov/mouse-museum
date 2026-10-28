#!/usr/bin/env python3
"""Stage every missing catalogue entry from a verified complete listing.

Usage: python3 scripts/import_catalogue.py index.json --cache /path/to/cache
Existing catalogue JSON and slugs are never changed during staging.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
NAMES={
 18:'Marsianka UVK-01 · dark grey (early)',61:'Marsianka UVK-01 · red',80:'Marsianka UVK-01 · black',
 210:'Marsianka UVK-01 · dark grey',211:'Marsianka UVK-01 · grey',223:'Marsianka UVK-01 · black and white',
 208:'Mouse 04.P (Poisk)',127:'Kometa NV 03.049.003 (Kolobok)',162:'ES 1842',192:'MTM-1 Mouse',
 69:'Ball Manipulator',154:'Kibord 007',190:'UVGI MAN-88',222:'DKSh-251',249:'BShRU',257:'Unitel City Kamyshin',
}
TRANSLIT=dict(zip('абвгдеёзийклмнопрстуфхцэ','abvgdeezijklmnoprstufhce'))
TRANSLIT.update({'ж':'zh','ч':'ch','ш':'sh','щ':'shch','ъ':'','ь':'','ю':'yu','я':'ya'})
def latin(text):
 return ''.join(TRANSLIT.get(c.lower(),c) for c in text)

def stage(index,cache):
 records=json.loads(index.read_text());assert len(records)==len({r['sourceId'] for r in records})
 existing=[json.loads(p.read_text()) for p in (ROOT/'content/mice').glob('*.json')]
 known={r['source'] for r in existing};order=max(r['order'] for r in existing)+1
 seeds=cache/'new-items';seeds.mkdir(parents=True,exist_ok=True)
 count=0
 for record in records:
  if record['source'] in known:continue
  page=cache/'pages'/f'{record["sourceId"]}.html';soup=BeautifulSoup(page.read_text(),'html.parser')
  assert soup.h1 and soup.select_one('.item-properties'),page
  ru=soup.h1.get_text(' ',strip=True);en=NAMES.get(record['sourceId'],latin(ru) if re.search('[А-Яа-я]',ru) else ru)
  base=unicodedata.normalize('NFKD',en).encode('ascii','ignore').decode().lower()
  slug=re.sub('[^a-z0-9]+','-',base).strip('-')+f'-{record["sourceId"]}'
  item={'id':f'MP-{record["sourceId"]:04}','slug':slug,'title':{'en':en,'ru':ru},'source':record['source'],
        'sourceOrder':record['sourceOrder'],'order':order,'sourceProperties':{},'photos':[],
        'manufacturer':{'en':'Not recorded','ru':'Не указан'},'brand':'Unknown','year':None,
        'tracking':{'key':'unknown','en':'Not recorded','ru':'Не указана'},'interface':None,'soviet':None,
        'features':{'en':'','ru':''},'description':{'en':'','ru':''},'notes':{'en':'','ru':''}}
  (seeds/f'{slug}.json').write_text(json.dumps(item,ensure_ascii=False,indent=2)+'\n');order+=1;count+=1
 (cache/'catalogue-index.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'sourceCount':len(records),'existing':len(existing),'stagedNew':count}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('index',type=Path);p.add_argument('--cache',type=Path,required=True);a=p.parse_args();stage(a.index,a.cache)
