#!/usr/bin/env python3
"""Independently compare every cached game resource with Python's LZMA decoder.

Requires an imported game and a populated asset cache; never modifies either.
"""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import plistlib
import struct


def locations(data):
    assert data[:4] == b"DTRZ"
    files, folders = struct.unpack_from("<HH", data, 4)
    position = 9
    for _ in range(files + folders - 1):
        position = data.index(0, position) + 1
    table = position + files * 6 + 4
    records = [struct.unpack_from("<IIII", data, table + i * 16)
               for i in range(files)]
    return table, records


def compare(source, cached):
    table, original = locations(source)
    decoded_table, decoded = locations(cached)
    assert table == decoded_table and source[:table] == cached[:table]
    offsets = sorted({record[0] for record in original} | {len(source)})
    total = 0
    for entry, (src, dst) in enumerate(zip(original, decoded, strict=True)):
        offset, size, size2, flags = src
        end = offsets[offsets.index(offset) + 1]
        compressed = source[offset:end]
        expected = (lzma.decompress(compressed, format=lzma.FORMAT_ALONE)
                    if flags == 0x200 else compressed[:size])
        assert len(expected) == size == size2
        target, output_size, output_size2, output_flags = dst
        assert (output_size, output_size2, output_flags) == (size, size2, flags)
        assert cached[target:target + size] == expected, f"Asset {entry} differs"
        total += size
    assert len(cached) == table + len(decoded) * 16 + total
    return len(decoded), total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(
        os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "redegpc")
    args = parser.parse_args()
    pointer = plistlib.loads((args.data / "current.plist").read_bytes())
    install = args.data / "installations" / pointer["Installation"]
    manifest = plistlib.loads((install / "manifest.plist").read_bytes())
    source_path = install / manifest["AppPath"] / "main.dz"
    source = source_path.read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    cache_path = args.data / "cache/assets-v1" / f"{source_hash}.dz"
    cached = cache_path.read_bytes()
    count, total = compare(source, cached)
    # The same comparison must reject a changed resource, so a broken checker
    # cannot mistake "no difference found" for successful byte verification.
    altered = bytearray(cached)
    altered[-1] ^= 1
    try:
        compare(source, altered)
    except AssertionError:
        pass
    else:
        raise AssertionError("Tamper control was accepted")
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
    print(json.dumps({"assets": count, "decoded_bytes": total,
                      "source_sha256": source_hash,
                      "cache_sha256": hashlib.sha256(cached).hexdigest(),
                      "tamper_control_rejected": True}, indent=2))
    print("ASSET_CACHE_VERIFIED")


if __name__ == "__main__":
    main()
