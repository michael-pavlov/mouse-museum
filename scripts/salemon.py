"""Render the unlisted collector landing with the shared bilingual museum shell."""
import posixpath
import re


def build(root, out, items, shell, asset):
    lisa = next(item for item in items if item['slug'] == 'apple-lisa-207')
    paths = {'ru': 'ru/salemon/index.html', 'en': 'en/salemon/index.html'}
    generated = []
    for language, path in [('ru', paths['ru']), ('en', paths['en']), ('ru', 'salemon/index.html')]:
        def relative(target):
            return posixpath.relpath(target, posixpath.dirname(path))

        body = (root / f'content/salemon/{language}.html').read_text()
        for alias, slug in [('ibm', 'ibm-6450350-30'), ('green', 'microsoft-green-eye'), ('lisa', 'apple-lisa-207')]:
            specimen = next(item for item in items if item['slug'] == slug)
            body = body.replace(f'assets/phone-{alias}.webp', specimen['photos'][0]['file'])
        body = re.sub(r'src="(assets/[^"]+)"', lambda match: f'src="{relative(match[1])}"', body)
        body = re.sub(r'href="\.\./ru/([^"]+)"',
                      lambda match: f'href="{relative(language + "/" + match[1])}"', body)
        head = (
            f'<link rel="stylesheet" href="{asset(path, "assets/salemon.css")}">'
        )
        title = ('SaleMonitor — сервис для коллекционеров' if language == 'ru'
                 else 'SaleMonitor — a service for collectors')
        description = ('Меньше поиска. Больше находок. Новые объявления по вашим запросам прямо в Telegram.'
                       if language == 'ru' else
                       'Less searching. More discoveries. Get new listings matching your searches in Telegram.')
        shell(path, language, title, description, body,
              paths['en' if language == 'ru' else 'ru'], lisa['photos'][0]['file'],
              extra_head=head, body_class='salemon')
        if path == 'salemon/index.html':
            # Keep the short URL usable, with the Russian language URL as canonical.
            dest = out / path
            rendered = dest.read_text()
            rendered = re.sub(r'(<link rel="canonical" href=")([^"]+)/salemon/(">)',
                              r'\1\2/ru/salemon/\3', rendered)
            dest.write_text(rendered)
        generated.append(path)
    return generated
