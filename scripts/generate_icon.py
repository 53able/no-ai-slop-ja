#!/usr/bin/env python3
"""標準ライブラリだけでNo AI Slop JAのアイコンPNGを生成する。"""

from __future__ import annotations

import binascii
import struct
import zlib
from pathlib import Path

SIZE = 256
BACKGROUND = (25, 50, 77, 255)
PAPER = (247, 244, 235, 255)
ACCENT = (224, 82, 82, 255)
INK = (25, 50, 77, 255)


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)


def inside_round_rect(x: int, y: int, left: int, top: int, right: int, bottom: int, radius: int) -> bool:
    if left + radius <= x < right - radius or top + radius <= y < bottom - radius:
        return left <= x < right and top <= y < bottom
    cx = left + radius if x < left + radius else right - radius - 1
    cy = top + radius if y < top + radius else bottom - radius - 1
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2


def pixel(x: int, y: int) -> tuple[int, int, int, int]:
    color = BACKGROUND
    if inside_round_rect(x, y, 47, 35, 209, 221, 18):
        color = PAPER
    if (72 <= y < 82 and 75 <= x < 181) or (72 <= y < 82 and 75 <= x < 181):
        color = INK
    if 105 <= y < 115 and 75 <= x < 181:
        color = INK
    if 138 <= y < 148 and 75 <= x < 151:
        color = INK
    # 定型文を消す赤い斜線。紙の外へ少しはみ出させ、既存ロゴを模倣しない。
    if abs((x + y) - 258) <= 9 and 47 <= x <= 211 and 47 <= y <= 211:
        color = ACCENT
    return color


def main() -> None:
    rows = []
    for y in range(SIZE):
        row = bytearray([0])
        for x in range(SIZE):
            row.extend(pixel(x, y))
        rows.append(bytes(row))
    raw = b"".join(rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    target = Path(__file__).resolve().parents[1] / "assets" / "no-ai-slop-ja.png"
    target.write_bytes(png)
    print(target.relative_to(target.parents[1]))


if __name__ == "__main__":
    main()
