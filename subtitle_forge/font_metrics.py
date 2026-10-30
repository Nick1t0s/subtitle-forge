"""Small, dependency-free TTF/OTF advance-width reader for ASS layout."""

from __future__ import annotations

import functools
import math
import os
import struct
import subprocess
import unicodedata


def _u16(data: bytes, pos: int) -> int:
    return struct.unpack_from(">H", data, pos)[0]


def _u32(data: bytes, pos: int) -> int:
    return struct.unpack_from(">I", data, pos)[0]


class _Font:
    def __init__(self, path: str):
        try:
            with open(path, "rb") as f:
                self.data = f.read()
        except OSError as exc:
            raise ValueError(f"Cannot read font file {path!r}; install the requested font and fontconfig.") from exc
        data = self.data
        if data[:4] == b"ttcf":
            raise ValueError(f"Font collection {path!r} is unsupported; install/use a standalone TTF or OTF font.")
        if len(data) < 12:
            raise ValueError(f"Invalid or unsupported font file {path!r}; install a valid TTF/OTF font.")

        n_tables = _u16(data, 4)
        tables: dict[bytes, tuple[int, int]] = {}
        for i in range(n_tables):
            p = 12 + 16 * i
            if p + 16 > len(data):
                break
            tag = data[p:p + 4]
            offset, length = _u32(data, p + 8), _u32(data, p + 12)
            if offset + length <= len(data):
                tables[tag] = (offset, length)

        try:
            head = tables[b"head"][0]
            hhea = tables[b"hhea"][0]
            hmtx = tables[b"hmtx"][0]
            cmap = tables[b"cmap"][0]
            self.units = _u16(data, head + 18)
            n_metrics = _u16(data, hhea + 34)
            cmap_offset = self._select_cmap(cmap)
        except (KeyError, IndexError, struct.error, ValueError) as exc:
            raise ValueError(f"Font {path!r} lacks usable TTF/OTF metrics; install a compatible font.") from exc
        if not self.units or not n_metrics:
            raise ValueError(f"Font {path!r} has invalid horizontal metrics; install a compatible font.")
        self.n_metrics = n_metrics
        self.hmtx = hmtx
        self.cmap_format, self.cmap_offset = cmap_offset
        self._glyph_count = _u16(data, tables[b"maxp"][0] + 4) if b"maxp" in tables else 65535

    def _select_cmap(self, cmap: int) -> tuple[int, int]:
        d = self.data
        n = _u16(d, cmap + 2)
        candidates: list[tuple[int, int, int]] = []
        for i in range(n):
            p = cmap + 4 + 8 * i
            platform, encoding, rel = _u16(d, p), _u16(d, p + 2), _u32(d, p + 4)
            off = cmap + rel
            fmt = _u16(d, off)
            # Prefer Unicode full-repertoire mappings, then BMP Unicode maps.
            rank = (0 if fmt == 12 and platform == 3 and encoding == 10 else
                    1 if fmt == 12 and platform == 0 else
                    2 if fmt == 4 and platform == 3 and encoding in (1, 10) else
                    3 if fmt == 4 and platform == 0 else 99)
            if rank < 99:
                candidates.append((rank, fmt, off))
        if not candidates:
            raise ValueError("No Unicode cmap format 4/12")
        _, fmt, off = min(candidates)
        return fmt, off

    def glyph(self, cp: int) -> int:
        d, p = self.data, self.cmap_offset
        if self.cmap_format == 12:
            n = _u32(d, p + 12)
            lo, hi = 0, n
            while lo < hi:
                mid = (lo + hi) // 2
                q = p + 16 + mid * 12
                start, end = _u32(d, q), _u32(d, q + 4)
                if cp < start:
                    hi = mid
                elif cp > end:
                    lo = mid + 1
                else:
                    return _u32(d, q + 8) + cp - start
            return 0

        # cmap format 4 covers the BMP (including Cyrillic).
        if cp > 0xFFFF:
            return 0
        seg_count = _u16(d, p + 6) // 2
        end_base = p + 14
        start_base = end_base + 2 * seg_count + 2
        delta_base = start_base + 2 * seg_count
        range_base = delta_base + 2 * seg_count
        lo, hi = 0, seg_count
        while lo < hi:
            mid = (lo + hi) // 2
            if cp > _u16(d, end_base + 2 * mid):
                lo = mid + 1
            else:
                hi = mid
        if lo >= seg_count or cp < _u16(d, start_base + 2 * lo):
            return 0
        delta = struct.unpack_from(">h", d, delta_base + 2 * lo)[0]
        ro_pos = range_base + 2 * lo
        ro = _u16(d, ro_pos)
        if not ro:
            return (cp + delta) & 0xFFFF
        glyph_pos = ro_pos + ro + 2 * (cp - _u16(d, start_base + 2 * lo))
        gid = _u16(d, glyph_pos)
        return (gid + delta) & 0xFFFF if gid else 0

    def advance(self, glyph: int) -> int:
        if glyph < self.n_metrics:
            return _u16(self.data, self.hmtx + glyph * 4)
        return _u16(self.data, self.hmtx + (self.n_metrics - 1) * 4)


@functools.lru_cache(maxsize=64)
def _resolve_font(font: str) -> _Font:
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", font + ":style=Bold"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"Cannot resolve font {font!r}; install fontconfig and the requested font.") from exc
    path = result.stdout.strip()
    if not path or not os.path.isfile(path):
        raise ValueError(f"Font {font!r} was not found; install it and refresh fontconfig.")
    try:
        return _Font(path)
    except ValueError as exc:
        raise ValueError(f"Cannot measure font {font!r} ({path}): {exc}") from exc


def measure_text(text: str, font: str, font_size: float) -> float:
    """Return the font's horizontal advance in pixels at ``font_size``.

    Widths are summed from the font's horizontal metrics (with a very small
    0.15% per-character safety allowance for ASS renderer rounding).
    """
    if not math.isfinite(font_size) or font_size < 0:
        raise ValueError("font_size must be finite and non-negative")
    metrics = _resolve_font(font)
    total = 0
    visible = 0
    for char in text:
        # Combining marks and format controls have no spacing advance.
        if unicodedata.category(char) in ("Mn", "Me", "Cf"):
            continue
        total += metrics.advance(metrics.glyph(ord(char)))
        visible += 1
    return total * font_size / metrics.units * (1.0 + 0.0015 * visible)
