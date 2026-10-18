#!/usr/bin/env python3
"""Independent PNG framing, CRC, zlib, filtering and pixel regression oracle."""
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zlib


def decode(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    offset, compressed, dimensions, ended = 8, bytearray(), None, False
    while offset < len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        name = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        assert len(payload) == length, (path, "truncated chunk")
        crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
        assert zlib.crc32(name + payload) == crc, (path, "CRC", name)
        if name == b"IHDR":
            assert dimensions is None and offset == 8
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            assert (depth, color, compression, filtering, interlace) == (8, 6, 0, 0, 0)
            dimensions = width, height
        elif name == b"IDAT":
            assert dimensions and not ended
            compressed.extend(payload)
        elif name == b"IEND":
            assert not payload
            ended = True
        else:
            raise AssertionError((path, "unexpected chunk", name))
        offset += length + 12
        if ended:
            break
    assert ended and offset == len(data), (path, "missing end or trailing bytes")
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed) + decoder.flush()
    assert decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
    width, height = dimensions
    stride = width * 4
    assert len(raw) == height * (stride + 1)
    pixels, previous = bytearray(), bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        filter_type = raw[start]
        assert filter_type in (0, 1), (path, "unexpected filter")
        row = bytearray(raw[start + 1:start + 1 + stride])
        if filter_type == 1:
            for x in range(4, stride):
                row[x] = (row[x] + row[x - 4]) & 255
        pixels.extend(row)
        previous = row
    return width, height, bytes(pixels)


def main():
    root = Path(__file__).resolve().parent.parent
    expected = json.loads((root / "gallery/expected.json").read_text())
    for name, golden in expected.items():
        width, height, pixels = decode(root / "gallery" / f"{name}.png")
        assert [width, height] == golden["size"], name
        assert hashlib.sha256(pixels).hexdigest() == golden["rgba_sha256"], name
        assert all(alpha == 255 for alpha in pixels[3::4]), (name, "poster opacity")
        assert len(set(pixels[::4])) > 100, (name, "gradient range")
        svg = (root / "gallery" / f"{name}.svg").read_text()
        document = ET.fromstring(svg)
        assert document.attrib["viewBox"] == f"0 0 {width} {height}"
        assert svg.startswith("<svg ") and svg.endswith("</svg>\n")
        assert "<path" in svg and "<linearGradient" in svg and "<image" not in svg
        print(f"{name}: {width} × {height}, PNG pixels + SVG paths verified")


if __name__ == "__main__":
    main()
