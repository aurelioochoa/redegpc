#!/usr/bin/env python3
"""Export generated launcher artwork without synthesizing or retouching pixels.

Requires Python 3, Pillow for inspection, and ImageMagick for PNG export.
Run from any working directory. Existing originals are never overwritten.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent / 'assets'
NEW_SIZES = {
    **{name: (512, 512) for name in (
        'achievement-handgun', 'achievement-punisher', 'achievement-shotgun',
        'achievement-riot-gun', 'achievement-tmp', 'achievement-rifle',
        'achievement-magnum', 'achievement-difficulty-easy',
        'achievement-difficulty-normal', 'achievement-difficulty-professional',
        'achievement-platinum')},
    'desk-background': (1920, 1080),
    'airport-blueprint': (1400, 900),
    'dossier-folder': (1000, 920),
    'detail-paper': (700, 720),
    'airport-stamp': (500, 220),
    'paperclip': (120, 320),
    'icon-logs': (80, 96),
}
ALIASES = {'case-paper': 'paper'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(path):
    with Image.open(path) as im:
        im.load()
        result = {'size': list(im.size), 'mode': im.mode,
                  'sha256': digest(path), 'bytes': path.stat().st_size}
        if 'A' in im.getbands():
            a = im.getchannel('A')
            histogram = a.histogram()
            result['alpha'] = {'range': list(a.getextrema()),
                               'transparent': histogram[0],
                               'opaque': histogram[255],
                               'bbox': a.getbbox()}
        return result


def export(allow_incomplete=False):
    jobs = json.loads((ROOT / 'prompts.json').read_text())
    expansion = ROOT / 'expansion-prompts.json'
    if expansion.exists():
        jobs += json.loads(expansion.read_text())
    missing = [j['name'] for j in jobs
               if not (ROOT / 'sources' / (j['name'] + '.png')).is_file()]
    if missing and not allow_incomplete:
        raise SystemExit('Missing generated sources: ' + ', '.join(missing))
    jobs = [job for job in jobs if job['name'] not in missing]
    baseline = json.loads((ROOT / 'baseline.json').read_text())
    manifest = {'generator': 'built-in image_gen', 'assets': [], 'aliases': ALIASES,
                'references': ['docs/launcher-concepts/03-incident-dossier.png',
                               'docs/launcher-concepts/04-achievements.png']}
    for job in jobs:
        name = job['name']
        src = ROOT / 'sources' / f'{name}.png'
        dst = ASSETS / f'{name}.png'
        if name in baseline:
            width, height = baseline[name]['size']
        else:
            width, height = NEW_SIZES[name]
        command = ['magick', str(src)]
        if job['alpha']:
            # Remove empty generation margins, then provide uniform clear padding.
            inner = f'{max(1, round(width * .94))}x{max(1, round(height * .94))}'
            command += ['-trim', '+repage', '-resize', inner, '-gravity', 'center',
                        '-background', 'none', '-extent', f'{width}x{height}',
                        '-define', 'png:color-type=6']
        else:
            command += ['-resize', f'{width}x{height}^', '-gravity', 'center',
                        '-extent', f'{width}x{height}', '-background', '#e4e0d8',
                        '-alpha', 'remove', '-alpha', 'off',
                        '-define', 'png:color-type=2']
        subprocess.run(command + [str(dst)], check=True)
        info = {'name': name, 'transparent': job['alpha'],
                'source': f'sources/{name}.png', 'source_info': inspect(src),
                'output': f'../assets/{name}.png', 'output_info': inspect(dst)}
        if name in baseline:
            info['original_info'] = baseline[name]
        manifest['assets'].append(info)
    for alias, source in ALIASES.items():
        target = ASSETS / f'{alias}.png'
        if (ASSETS / f'{source}.png').exists():
            target.write_bytes((ASSETS / f'{source}.png').read_bytes())
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    preview(jobs)
    print(f'PARTIAL EXPORT: {len(jobs)} ready, {len(missing)} generating' if missing
          else 'LAUNCHER_ARTWORK_EXPORTED')


def preview(jobs):
    # Contact sheet is review evidence, never used as production artwork.
    width, height, columns = 330, 250, 5
    sheet = Image.new('RGB', (columns * width,
                     ((len(jobs) + columns - 1) // columns) * height), '#242a30')
    for index, job in enumerate(jobs):
        tile = Image.new('RGB', (width, height), '#ddd9d0')
        draw = ImageDraw.Draw(tile)
        draw.rectangle((width // 2, 0, width, height - 35), fill='#26323e')
        with Image.open(ASSETS / (job['name'] + '.png')) as original:
            im = original.convert('RGBA')
            im.thumbnail((width - 24, height - 55), Image.Resampling.LANCZOS)
            tile.paste(im, ((width - im.width) // 2, (height - 35 - im.height) // 2), im)
        draw.rectangle((0, height - 35, width, height), fill='#242a30')
        draw.text((8, height - 25), job['name'], fill='white')
        sheet.paste(tile, ((index % columns) * width, (index // columns) * height))
    sheet.save(ROOT / 'after.jpg', quality=92)


if __name__ == '__main__':
    export(allow_incomplete='--available' in sys.argv)
