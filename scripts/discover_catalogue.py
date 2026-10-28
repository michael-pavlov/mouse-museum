#!/usr/bin/env python3
"""Validate cached listing pagination and extract the complete public catalogue.

python3 scripts/discover_catalogue.py listing-1.html listing-2.html ... --output index.json
Requires BeautifulSoup (requirements-import.txt). No network or mutations of items.
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from bs4 import BeautifulSoup


def discover(files):
    entries=[];seen=set();expected=None
    for page,file in enumerate(files,1):
        soup=BeautifulSoup(file.read_text(),'html.parser')
        count=soup.select_one('.title-count');assert count,f'No collection count: {file}'
        declared=int(re.search(r'\d+',count.get_text())[0])
        if expected is None:expected=declared
        assert declared==expected,'Catalogue changed while reading its pages'
        for a in soup.select('ul.collection li a[href]'):
            if not re.fullmatch('/collections/old-mice/\d+/',a['href']):continue
            ident=int(a['href'].strip('/').rsplit('/',1)[-1])
            assert ident not in seen,f'Duplicate item across listing pages: {ident}'
            seen.add(ident)
            entries.append({'sourceId':ident,'source':'https://collectionerus.ru'+a['href'],
                            'title':a.get('title') or a.get_text(' ',strip=True),'sourceOrder':len(entries)})
        next_link=soup.select_one('link[rel=next]')
        if page<len(files):
            assert next_link and parse_qs(urlsplit(next_link['href']).query).get('page')==[str(page+1)],f'Missing next page: {file}'
        else:
            assert not next_link,'Listing is incomplete: another page exists'
    assert len(entries)==expected,f'Expected {expected} records, found {len(entries)}'
    return entries

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('pages',type=Path,nargs='+');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    records=discover(args.pages);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    print(f'Complete listing verified: {len(records)} records on {len(args.pages)} pages.')
