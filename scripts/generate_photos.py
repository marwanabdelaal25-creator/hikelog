#!/usr/bin/env python3
"""Generate noise-filled PNG trail photo fixtures (stdlib only)."""

from __future__ import annotations

import random
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "photos"


def _chunk(name: bytes, data: bytes) -> bytes:
    return (
        len(data).to_bytes(4, "big")
        + name
        + data
        + zlib.crc32(name + data).to_bytes(4, "big")
    )


def fake_png(width: int = 72, height: int = 72, seed: int = 0) -> bytes:
    rng = random.Random(seed)
    out = bytearray(PNG_SIGNATURE)
    out += _chunk(
        b"IHDR",
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00",
    )
    rows = bytearray()
    for _ in range(height):
        rows.append(0)
        rows.extend(rng.randbytes(width * 3))
    out += _chunk(b"IDAT", zlib.compress(bytes(rows), 1))
    out += _chunk(b"IEND", b"")
    return bytes(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20260607)
    count = 520
    w, h = 72, 72
    total = 0
    for i in range(count):
        seed = rng.randint(0, 2**31 - 1)
        data = fake_png(w, h, seed=seed)
        path = OUT / f"trail_photo_{i:05d}.png"
        path.write_bytes(data)
        total += len(data)
    print(f"wrote {count} photos to {OUT} ({total / (1024 * 1024):.2f} MB raw)")


if __name__ == "__main__":
    main()
