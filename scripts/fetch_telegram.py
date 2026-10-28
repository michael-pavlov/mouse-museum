#!/usr/bin/env python3
"""Archive the public channel feed and available media, without Telegram login.

Run before import_telegram.py. New posts require English translations and
bilingual excerpts before offline import. Use --refresh to refetch HTML;
already downloaded media are reused.
"""
import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from import_telegram import markdown_node

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data/source/telegram'
CHANNEL = 'old_mice_and_hw'


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(dest.suffix + '.download')
    subprocess.run(['curl', '-L', '--fail', '--silent', '--show-error', '--max-time', '90', '--retry', '2', url, '-o', str(temp)], check=True)
    temp.replace(dest)


def parse_message(message):
    text = message.select_one('.tgme_widget_message_text')
    date = message.select_one('time[datetime]')
    photos = []
    selectors = '.tgme_widget_message_photo_wrap'
    if not message.select(selectors):
        selectors = '.link_preview_image,.tgme_widget_message_video_thumb'
    for element in message.select(selectors):
        match = re.search(r"url\(['\"]?([^)'\"]+)", element.get('style', ''))
        if match and match[1].startswith('https:') and match[1] not in photos:
            photos.append(match[1])
    question = message.select_one('.tgme_widget_message_poll_question')
    return {'source':'https://t.me/'+message['data-post'], 'date':date['datetime'] if date else None,
            'html':str(text) if text else '', 'text':text.get_text() if text else '',
            'markdown':markdown_node(text).strip() if text else '', 'photos':photos,
            'video':bool(message.select('video,.tgme_widget_message_video_player')),
            'videos':[v['src'] for v in message.select('video[src]')],
            'poll':{'question':question.get_text(strip=True), 'options':[e.get_text(strip=True) for e in message.select('.tgme_widget_message_poll_option_text')]} if question else None}


def download_media(task):
    url, dest = task
    if not dest.exists():
        fetch(url, dest)
    if dest.suffix == '.jpg':
        with Image.open(dest) as image:
            image.load()
            image = image.convert('RGB')
            image.thumbnail((1800, 1800))
            image.save(dest.with_suffix('.webp'), quality=88)
    return {'file':dest.relative_to(ROOT).as_posix(), 'bytes':dest.stat().st_size,
            'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    url = f'https://t.me/s/{CHANNEL}'
    dest = SOURCE/'latest.html'
    seen, posts = set(), {}
    reached_start = False
    while True:
        if args.refresh or not dest.exists():
            fetch(url, dest)
        soup = BeautifulSoup(dest.read_text(), 'html.parser')
        messages = soup.select('[data-post]')
        if not messages:
            break
        for message in messages:
            posts[message['data-post']] = parse_message(message)
        before = min(int(m['data-post'].rsplit('/',1)[-1]) for m in messages)
        print(f'{len(posts)} records; oldest message {before}', flush=True)
        if before == 1:
            reached_start = True
            break
        if before in seen:
            break
        seen.add(before)
        url = f'https://t.me/s/{CHANNEL}?before={before}'
        dest = SOURCE/f'before-{before}.html'
    if not reached_start:
        raise SystemExit('The first message was not reached. Refusing to replace the complete archive.')
    archive = sorted(posts.values(), key=lambda p:(p['date'] or '',int(p['source'].rsplit('/',1)[-1])))
    (SOURCE/'posts.json').write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n')
    tasks = []
    for post in archive:
        id = post['source'].rsplit('/',1)[-1]
        for i, media_url in enumerate(post['photos'], 1):
            tasks.append((media_url, ROOT/f'assets/posts/telegram-{id}/{i:02}.jpg'))
        for i, media_url in enumerate(post['videos'], 1):
            tasks.append((media_url, ROOT/f'assets/posts/telegram-{id}/video-{i:02}.mp4'))
    manifest, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(download_media, task):task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            try:
                manifest.append(future.result())
            except Exception as error:
                errors.append({'file':str(futures[future][1]), 'error':str(error)})
    (SOURCE/'media-manifest.json').write_text(json.dumps(sorted(manifest,key=lambda m:m['file']),indent=2)+'\n')
    (SOURCE/'media-errors.json').write_text(json.dumps(errors,indent=2)+'\n')
    print(f'{len(archive)} records, {len(manifest)} media files, {len(errors)} failures')
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
