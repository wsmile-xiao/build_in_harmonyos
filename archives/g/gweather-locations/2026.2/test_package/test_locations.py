#!/usr/bin/env python3
"""Consumer verification for gweather-locations 2026.2 Locations.bin.

Fully parses the GVariant normal-form database (little-endian serialisation,
the armv8 OHOS host endian) in pure python — the same byte format libgweather
reads at runtime — and validates:

  * FILETYPE_MAGIC 0x5747687442443130 ("GWthDB01" as u64 LE; on-disk bytes
    "01DBthGW")
  * the complete top-level structure
    (t a{sq} a{sq} a{s((ss)as)} a((ss)ss(dd)ssqyqqaqaq))
  * referential integrity: every children/parent/nearest/tz-hint/zones
    index and every country/METAR table entry must be in range (this is
    what corrupt serialisation would break first)
  * well-known entries: Europe/Paris + America/New_York timezones,
    Paris/London/Tokyo cities, LFPG METAR station

Exit 0 = all checks pass ("PASS" lines printed); 1 = failure.
"""
import struct
import sys

FILETYPE_MAGIC = 0x5747687442443130
TOP_TYPE = "(ta{sq}a{sq}a{s((ss)as)}a((ss)ss(dd)ssqyqqaqaq))"
INVALID_IDX = 0xFFFF

_ALIGN = {"y": 1, "b": 1, "n": 2, "q": 2, "i": 4, "u": 4, "x": 8, "t": 8,
          "d": 8, "s": 1, "o": 1, "g": 1}
_FIXED = {"y": ("B", 1), "b": (None, 1), "n": ("h", 2), "q": ("H", 2),
          "i": ("i", 4), "u": ("I", 4), "x": ("q", 8), "t": ("Q", 8),
          "d": ("d", 8)}


def _align_up(pos, a):
    return (pos + a - 1) & ~(a - 1)


def _offset_width(size):
    """GVariant framing-offset byte width: the smallest of 1/2/4/8 that can
    express the full serialised container size (symmetric to what the
    serialiser does when it sizes its offset table)."""
    if size <= 0xFF:
        return 1
    if size <= 0xFFFF:
        return 2
    if size <= 0xFFFFFFFF:
        return 4
    return 8


def _one_type(s, i):
    """Return (complete type string, next index) for the type starting at i."""
    c = s[i]
    if c in "ybnqiuxtdsog":
        return c, i + 1
    if c == "a":
        inner, j = _one_type(s, i + 1)
        return "a" + inner, j
    if c in "({":
        close = ")" if c == "(" else "}"
        depth, j = 0, i
        while j < len(s):
            if s[j] == c:
                depth += 1
            elif s[j] == close:
                depth -= 1
                if depth == 0:
                    return s[i:j + 1], j + 1
            j += 1
        raise ValueError("unbalanced type at %d in %s" % (i, s))
    raise ValueError("bad type char %r in %s" % (c, s))


def _split(body):
    """Split a tuple/dict-entry body into its complete child type strings."""
    out, i = [], 0
    while i < len(body):
        t, i = _one_type(body, i)
        out.append(t)
    return out


def _align(t):
    c = t[0]
    if c in _ALIGN:
        return _ALIGN[c]
    if c == "a":
        return _align(t[1:])
    if c in "({":
        return max(_align(ct) for ct in _split(t[1:-1]))
    raise ValueError("unsupported type %r" % t)


def _fixed_size(t):
    """Byte size when fully determined by the type, else None (arrays and
    strings are always variable; parents then need framing offsets)."""
    c = t[0]
    if c in _FIXED:
        return _FIXED[c][1]
    if c in "sog" or c == "a":
        return None
    if c in "({":
        total = 0
        for ct in _split(t[1:-1]):
            fs = _fixed_size(ct)
            if fs is None:
                return None
            total = _align_up(total, _align(ct)) + fs
        return total
    raise ValueError("unsupported type %r" % t)


class GVariantReader:
    """Recursive deserializer for the GVariant serialised normal form."""

    def __init__(self, data):
        self.d = data

    def value(self, t, start, end):
        c = t[0]
        if c in _FIXED:
            fmt, _size = _FIXED[c]
            pos = _align_up(start, _ALIGN[c])
            if fmt is None:  # boolean
                return self.d[pos] != 0
            return struct.unpack_from("<" + fmt, self.d, pos)[0]
        if c in "sog":
            nul = self.d.index(b"\x00", start, end)
            return self.d[start:nul].decode("utf-8")
        if c == "a":
            return self.array(t[1:], start, end)
        if c in "({":
            return self.struct(_split(t[1:-1]), start, end,
                               as_pair=(c == "{"))
        raise ValueError("unsupported type %r" % t)

    def struct(self, children, start, end, as_pair):
        # GVariant tuples/dict-entries store one framing offset for every
        # non-fixed-size child except the last, in REVERSE child order,
        # little endian, at the width dictated by the container size.
        n_off = sum(1 for idx, ct in enumerate(children)
                    if _fixed_size(ct) is None and idx != len(children) - 1)
        size = end - start
        if n_off == 0:
            body_end, offs = size, None
        else:
            w = _offset_width(size)
            if size < w * n_off:
                raise ValueError("framing table overruns tuple at [%d,%d)"
                                 % (start, end))
            body_end = size - w * n_off
            raw = self.d[start + body_end:start + size]
            stored = [int.from_bytes(raw[k * w:(k + 1) * w], "little")
                      for k in range(n_off)]
            offs = stored[::-1]
            if any(offs[k] < offs[k - 1] for k in range(1, n_off)):
                raise ValueError("non-monotonic tuple framing at [%d,%d)"
                                 % (start, end))
            if offs[-1] > body_end:
                raise ValueError("tuple framing past body at [%d,%d)"
                                 % (start, end))
            # The last child always extends to the start of the offset
            # table; when it is fixed-size this yields an equality that
            # pins the frame, and when variable-size the recursive parse
            # (and the index checks below) catch any inconsistency.
            last_t = children[-1]
            last_fs = _fixed_size(last_t)
            if last_fs is not None:
                pos = _align_up(start + offs[-1], _align(last_t))
                if pos + last_fs != start + body_end:
                    raise ValueError("fixed last child does not reach "
                                     "tuple body end at [%d,%d)"
                                     % (start, end))
        vals = [None] * len(children)
        cur = start
        fi = 0
        for idx, ct in enumerate(children):
            pos = _align_up(cur, _align(ct))
            fs = _fixed_size(ct)
            if fs is not None:
                vals[idx] = self.value(ct, pos, pos + fs)
                cur = pos + fs
                continue
            if idx == len(children) - 1:
                e = start + body_end
            else:
                e = start + offs[fi]
                fi += 1
            vals[idx] = self.value(ct, pos, e)
            cur = e
        if as_pair:
            return vals[0], vals[1]
        return vals

    def array(self, et, start, end):
        size = end - start
        if size == 0:
            return []
        a = _align(et)
        base = _align_up(start, a)
        fs = _fixed_size(et)
        if fs is not None:
            out, pos = [], base
            while pos + fs <= end:
                out.append(self.value(et, pos, pos + fs))
                pos += fs
            return out
        # Variable-size elements: one framing offset per element (including
        # the last), FORWARD order, width dictated by the container size.
        # The final offset equals the extent of the element data, which
        # yields the element count: size - last_offset == w * count.
        w = _offset_width(size)
        last = int.from_bytes(self.d[end - w:end], "little")
        count, rem = divmod(size - last, w)
        if rem or count < 1 or last > size - w:
            raise ValueError("bad array framing at [%d,%d)" % (start, end))
        body_end = size - w * count
        raw = self.d[start + body_end:end]
        offs = [int.from_bytes(raw[k * w:(k + 1) * w], "little")
                for k in range(count)]
        if offs[-1] != body_end:
            raise ValueError("array last offset mismatch at [%d,%d)"
                             % (start, end))
        if any(offs[k] < offs[k - 1] for k in range(1, count)):
            raise ValueError("non-monotonic array framing at [%d,%d)"
                             % (start, end))
        out, cur = [], start
        for k in range(count):
            pos = _align_up(cur, a)
            e = start + offs[k]
            out.append(self.value(et, pos, e))
            cur = e
        return out


def main():
    if len(sys.argv) != 2:
        print("usage: test_locations.py <Locations.bin>")
        return 2
    with open(sys.argv[1], "rb") as f:
        data = f.read()

    failures = []

    def check(name, cond):
        if cond:
            print("PASS: %s" % name)
        else:
            print("FAIL: %s" % name)
            failures.append(name)

    check("database size sane (%d bytes)" % len(data), len(data) > 100000)
    magic = struct.unpack_from("<Q", data, 0)[0]
    check("FILETYPE_MAGIC u64 0x5747687442443130 (bytes '01DBthGW')",
          magic == FILETYPE_MAGIC)

    db = GVariantReader(data).value(TOP_TYPE, 0, len(data))
    check("top level fully parses into 5 members of %s" % TOP_TYPE,
          isinstance(db, list) and len(db) == 5)
    magic2, by_country, by_metar, timezones, locations = db
    check("embedded magic equals header magic", magic2 == magic)

    n_loc = len(locations)
    n_tz = len(timezones)
    print("INFO: locations=%d timezones=%d countries=%d metar=%d"
          % (n_loc, n_tz, len(by_country), len(by_metar)))
    check("locations >= 2000", n_loc >= 2000)
    check("timezones >= 100", n_tz >= 100)
    check("country table >= 100 entries", len(by_country) >= 100)
    check("METAR table >= 100 entries", len(by_metar) >= 100)

    tz_ids = set(k for k, _v in timezones)
    check("Europe/Paris timezone present", "Europe/Paris" in tz_ids)
    check("America/New_York timezone present", "America/New_York" in tz_ids)

    idx_ok = True
    for loc in locations:
        (_name, _zone, _radar, _coord, _cc, _code, tz_hint, _level,
         nearest, parent, children, zones) = loc
        for i in children:
            if not 0 <= i < n_loc:
                idx_ok = False
        for i in (nearest, parent):
            if i != INVALID_IDX and not 0 <= i < n_loc:
                idx_ok = False
        if tz_hint != INVALID_IDX and not 0 <= tz_hint < n_tz:
            idx_ok = False
        for z in zones:
            if not 0 <= z < n_tz:
                idx_ok = False
    check("all children/parent/nearest/tz-hint/zones indices in range",
          idx_ok)
    check("country index entries in range",
          all(0 <= v < n_loc for _k, v in by_country))
    check("METAR index entries in range",
          all(0 <= v < n_loc for _k, v in by_metar))

    cities = set(loc[0][0] for loc in locations if loc[7] == 4)
    check("Paris city present", "Paris" in cities)
    names = set(loc[0][0] for loc in locations)
    check("London entries present", "London" in names)
    check("Tokyo entries present", "Tokyo" in names)
    metar_ids = set(k for k, _v in by_metar)
    check("LFPG METAR station present", "LFPG" in metar_ids)

    if failures:
        print("FAILED: %d check(s): %s" % (len(failures), ", ".join(failures)))
        return 1
    print("ALL PASS: Locations.bin parsed and validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
