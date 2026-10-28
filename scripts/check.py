#!/usr/bin/env python3
"""Check emitted HTML and local links, including nested Pages deployments."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[1]/'dist'
class Page(HTMLParser):
 def __init__(self):super().__init__();self.refs=[];self.ids=set();self.h1=0;self.lang=None
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='html':self.lang=d.get('lang')
  if tag=='h1':self.h1+=1
  if 'id' in d:
   assert d['id'] not in self.ids, 'Duplicate HTML id: '+d['id']
   self.ids.add(d['id'])
  for attr in ('href','src'):
   if attr in d:self.refs.append(d[attr])
count=0
for p in ROOT.rglob('*.html'):
 if p.name=='404.html':continue
 page=Page();page.feed(p.read_text());assert page.lang in ('en','ru'),p;assert page.h1==1,p
 for ref in page.refs:
  url=urlsplit(ref)
  if url.scheme or url.netloc or not url.path:continue
  assert not url.path.startswith('/'),f'Root-relative link breaks repository subpaths: {p}: {ref}'
  target=(p.parent/unquote(url.path)).resolve()
  assert target.is_relative_to(ROOT.resolve()),(p,ref)
  if target.is_dir():target=target/'index.html'
  assert target.exists(),f'Broken link: {p}: {ref}'
  count+=1
print(f'OK: {count} local references; all catalogue and item pages have one h1 and a language.')
