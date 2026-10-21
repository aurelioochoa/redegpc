#!/usr/bin/env python3
"""Validate generated exports, original compatibility and independent sources."""
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    expected = actual = {entry['name'] for entry in manifest['assets']}
    assert len(expected) == len(manifest['assets']), 'Duplicate asset'
    assert set((root / 'sources').glob('*.png')) == {
        root / 'sources' / f'{name}.png' for name in expected}, 'Source set mismatch'
    source_hashes = set()
    for entry in manifest['assets']:
        name = entry['name']
        for key, info_key in [('source', 'source_info'), ('output', 'output_info')]:
            path = root / entry[key]
            assert path.is_file(), f'Missing {path}'
            assert sha(path) == entry[info_key]['sha256'], f'Digest mismatch: {name}'
            with Image.open(path) as im:
                im.load()
                assert list(im.size) == entry[info_key]['size'], f'Size: {name}'
                assert im.format == 'PNG', f'Not PNG: {name}'
                if entry['transparent']:
                    assert 'A' in im.getbands(), f'No alpha: {name}'
                    hist = im.getchannel('A').histogram()
                    assert hist[0] > im.width * im.height * .005, f'No clear margin: {name}'
                    # Ink overlays intentionally use partial opacity; resampling
                    # can also round solid material alpha from 255 to 254.
                    threshold = 128 if name == 'airport-blueprint' else 240
                    assert sum(hist[threshold:]) > 20, f'Insufficient painted opacity: {name}'
        output = entry['output_info']
        if 'original_info' in entry:
            assert output['size'] == entry['original_info']['size'], f'Changed dimensions: {name}'
            assert output['sha256'] != entry['original_info']['sha256'], f'Not regenerated: {name}'
        assert entry['source_info']['sha256'] not in source_hashes, f'Reused source: {name}'
        source_hashes.add(entry['source_info']['sha256'])
    assets = root.parent / 'assets'
    for alias, source in manifest['aliases'].items():
        path = assets / f'{alias}.png'
        assert path.is_file(), f'Missing alias: {alias}'
        assert sha(path) == sha(assets / f'{source}.png'), f'Drifted alias: {alias}'
    assert {p.stem for p in assets.glob('*.png')} == expected | set(manifest['aliases']), 'Obsolete or missing production asset'
    catalog_path = root.parent / 'achievements.json'
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text())['achievements']
        ids = {entry['id'] for entry in catalog}
        assert len(ids) == len(catalog), 'Duplicate achievement id'
        assert {entry['asset'] for entry in catalog} == {
            f'assets/{name}.png' for name in expected if name.startswith('achievement-')
        }, 'Achievement catalog/artwork mismatch'
        platinum = next(entry for entry in catalog if entry['id'] == 'platinum')
        assert platinum['unlock_rule']['type'] == 'all_other_achievements'
        assert set(platinum['unlock_rule']['required_ids']) == ids - {'platinum'}, 'Incomplete platinum dependency set'
        for entry in catalog:
            assert (root.parent / entry['asset']).is_file(), f'Missing achievement image: {entry["id"]}'
    for name in ('photo-leon', 'photo-claire', 'photo-protagonists'):
        with Image.open(assets / f'{name}.png') as im:
            pixels = im.convert('RGB').resize((80, 80))
            colored = sum(max(rgb) - min(rgb) > 25 for y in range(80)
                          for x in range(80) for rgb in [pixels.getpixel((x, y))])
            assert colored > 640, f'Portrait lacks color: {name}'
    return len(actual), len(manifest['aliases'])


if __name__ == '__main__':
    count, aliases = verify(ROOT)
    print(f'LAUNCHER_ARTWORK_VERIFIED: {count} independent generated assets, {aliases} compatibility alias')
