"""Generate FAT (explicit-transition) TZif v2 test fixtures for cxxtools.

Why this script exists: the cxxtools 3.0 `tz` unit suite (`test/tz-test.cpp`)
reads IANA timezone files through `$TZDIR/<name>` (default
`/usr/share/zoneinfo`, absent on HarmonyOS). The recipe must materialize
three files at test time into a writable TZDIR (TMPDIR on the device):
`Europe/Berlin`, `Pacific/Samoa`, `UTC`. They are committed nowhere as
binaries: CI restores PRs via `curl .../pull.diff + git apply`, which cannot
carry GIT binary patches, so vendored binaries break checkout. Everything
here is UTF-8 text; the binaries are produced on the test machine only.

- `Europe/Berlin`: 60 authentic historical transitions (1893-1996, kept
  verbatim from the IANA data, embedded below) plus 83 explicit transitions
  generated from the file's own POSIX footer rule
  (`CET-1CEST,M3.5.0,M10.5.0/3`, i.e. last Sunday of March/October at
  01:00 UTC) covering October 1996 through October 2037. The pip `tzdata`
  wheels ship IANA "slim" files whose explicit transitions for Europe/Berlin
  end on 1996-03-31; later dates are governed by the POSIX footer, which the
  cxxtools 3.0 `Tz` parser does not read. With a slim file every 2018 test
  date would wrongly resolve to CEST (+2).
- `Pacific/Samoa` (146 bytes) and `UTC` (111 bytes): verbatim IANA bytes
  (base64 below; provenance: PyPI `tzdata` package). Samoa's explicit
  transitions end in 1911 with the last type fixed at SST (UTC-11), still
  correct for the 2018 test dates; UTC has zero transitions and a single
  UTC type. They are static and tiny, so they are reproduced from text
  instead of a network/system lookup (the device has no zoneinfo tree).

Usage:
  python generate_berlin_fat.py --all <tzdir>     # generate all 3 fixtures
  python generate_berlin_fat.py <out-berlin>       # self-contained Berlin
  python generate_berlin_fat.py <slim-berlin> <out-berlin>  # legacy: from slim
"""
import base64
import calendar
import os
import struct
import sys

# --- Embedded authentic Berlin history (IANA data, 60 transitions) ---
TIMES60 = [
    -2422054408, -1693706400, -1680483600, -1663455600, -1650150000,
    -1632006000, -1618700400, -938905200, -857257200, -844556400,
    -828226800, -812502000, -796777200, -781052400, -776563200,
    -765936000, -761180400, -748479600, -733273200, -717631200,
    -714610800, -710380800, -701910000, -684975600, -670460400,
    -654130800, -639010800, 323830800, 338950800, 354675600,
    370400400, 386125200, 401850000, 417574800, 433299600,
    449024400, 465354000, 481078800, 496803600, 512528400,
    528253200, 543978000, 559702800, 575427600, 591152400,
    606877200, 622602000, 638326800, 654656400, 670381200,
    686106000, 701830800, 717555600, 733280400, 749005200,
    764730000, 780454800, 796179600, 811904400, 828234000,
]
IDX60 = [
    2, 1, 2, 1, 2, 1, 2, 1, 2, 1,
    2, 1, 2, 1, 3, 1, 2, 1, 2, 1,
    3, 1, 2, 1, 2, 1, 2, 1, 2, 1,
    2, 1, 2, 1, 2, 1, 2, 1, 2, 1,
    2, 1, 2, 1, 2, 1, 2, 1, 2, 1,
    2, 1, 2, 1, 2, 1, 2, 1, 2, 1,
]
# Berlin ttinfo types: 0:LMT +3208 | 1:CEST +7200 dst | 2:CET +3600 |
# 3:CEMT +10800 dst; abbr table and POSIX footer from the same IANA file.
TYPES = [(3208, 0, 0), (7200, 1, 4), (3600, 0, 9), (10800, 1, 13)]
ABBR = b'LMT\x00CEST\x00CET\x00CEMT\x00'
FOOTER = b'\nCET-1CEST,M3.5.0,M10.5.0/3\n'
V1HEAD = b'TZif2' + b'\0' * 15 + struct.pack('>6l', 0, 0, 0, 0, 1, 1)
V1DATA = b'\x00\x00\x00\x00\x00\x00\x00'

SAMOA_B64 = (
    'VFppZjIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAEAAA'
    'AAAAAAVFppZjIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAAwAA'
    'AAj/////bj3ICP////+RBfsIAQIAALF4AAD//1/4AAD//2VQAARMTVQAU1NUAAp'
    'TU1QxMQo='
)
UTC_B64 = (
    'VFppZjIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAEAAA'
    'AAAAAAVFppZjIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA'
    'AAQAAAAAAABVVEMAClVUQzAK'
)


def read_slim(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'TZif', 'bad magic'
    g, s, l, t, y, c = struct.unpack('>6l', d[20:44])
    v1head = d[:44]
    v1data = d[44:44 + 4 * t + t + 6 * y + c + 8 * l + s + g]
    h2 = 44 + len(v1data)
    assert d[h2:h2 + 4] == b'TZif', 'bad v2 magic'
    assert d[h2 + 4] == ord('2'), 'expected TZif version 2'
    g2, s2, l2, t2, y2, c2 = struct.unpack('>6l', d[h2 + 20:h2 + 44])
    assert (g2, s2, l2) == (0, 0, 0), 'unexpected leap/std/gmt data'
    off = h2 + 44
    times = list(struct.unpack('>%dq' % t2, d[off:off + 8 * t2]))
    idx = list(d[off + 8 * t2:off + 8 * t2 + t2])
    toff = off + 8 * t2 + t2
    types = [struct.unpack('>lBB', d[toff + 6 * i:toff + 6 * i + 6])
             for i in range(y2)]
    abbr = d[toff + 6 * y2:toff + 6 * y2 + c2]
    footer = d[toff + 6 * y2 + c2:]
    return v1head, v1data, (g2, s2, l2, y2, c2), times, idx, types, abbr, footer


def last_sunday(year, month):
    lastday = calendar.monthrange(year, month)[1]
    d = lastday
    while calendar.weekday(year, month, d) != 6:  # Monday=0 .. Sunday=6
        d -= 1
    return d


def epoch_utc(year, month, day):
    return calendar.timegm((year, month, day, 1, 0, 0))


def build_berlin(v1head, v1data, y2, c2, times, idx, types, abbr, footer):
    # Berlin types from the authentic file:
    #   0: LMT +3208 | 1: CEST +7200 dst | 2: CET +3600 | 3: CEMT +10800 dst
    assert types[1][:2] == (7200, 1), types
    assert types[2][:2] == (3600, 0), types
    assert times[-1] == epoch_utc(1996, 3, 31), times[-1]
    assert idx[-1] == 1, idx[-1]

    gen = []
    for year in range(1996, 2038):
        if year == 1996:
            # March 1996 already present; only October remains this year.
            gen.append((epoch_utc(year, 10, last_sunday(year, 10)), 2))
        else:
            gen.append((epoch_utc(year, 3, last_sunday(year, 3)), 1))
            gen.append((epoch_utc(year, 10, last_sunday(year, 10)), 2))
    # Stop at Oct 2037 so every stamp stays below 2^31 (32-bit time_t safe).
    gen = [(t, i) for (t, i) in gen
           if t <= epoch_utc(2037, 10, last_sunday(2037, 10))]
    assert gen[0][0] > times[-1], 'generated must continue history'
    assert all(b > a for a, b in zip([times[-1]] + [t for t, _ in gen[:-1]],
                                     [t for t, _ in gen])), 'strictly increasing'
    # Alternation: ..., CEST(1) -> CET(2) -> CEST(1) ...
    seq = [idx[-1]] + [i for _, i in gen]
    assert all(a != b for a, b in zip(seq, seq[1:])), 'must alternate'

    times2 = times + [t for t, _ in gen]
    idx2 = idx + [i for _, i in gen]
    t2 = len(times2)
    v2head = b'TZif2' + b'\0' * 15 + struct.pack('>6l', 0, 0, 0, t2, y2, c2)
    return b''.join([
        v1head, v1data, v2head,
        struct.pack('>%dq' % t2, *times2),
        bytes(idx2),
        b''.join(struct.pack('>lBB', *tp) for tp in types),
        abbr, footer,
    ]), len(times), len(gen), t2


def write_self_contained_berlin(dst):
    out, nhist, ngen, total = build_berlin(
        V1HEAD, V1DATA, 4, 18, list(TIMES60), list(IDX60),
        list(TYPES), ABBR, FOOTER)
    open(dst, 'wb').write(out)
    print('wrote %s: %d transitions (%d historical + %d generated)'
          % (dst, total, nhist, ngen))


def write_all(tzdir):
    os.makedirs(os.path.join(tzdir, 'Europe'), exist_ok=True)
    os.makedirs(os.path.join(tzdir, 'Pacific'), exist_ok=True)
    write_self_contained_berlin(os.path.join(tzdir, 'Europe', 'Berlin'))
    for name, blob in (('Pacific/Samoa', SAMOA_B64), ('UTC', UTC_B64)):
        dst = os.path.join(tzdir, *name.split('/'))
        open(dst, 'wb').write(base64.b64decode(blob))
        print('wrote %s: %d bytes' % (dst, os.path.getsize(dst)))


def main():
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == '--all':
        write_all(args[1])
    elif len(args) == 1:
        write_self_contained_berlin(args[0])
    elif len(args) == 2:
        src, dst = args
        v1head, v1data, counts, times, idx, types, abbr, footer = \
            read_slim(src)
        _, _, _, y2, c2 = counts
        out, nhist, ngen, total = build_berlin(
            v1head, v1data, y2, c2, times, idx, types, abbr, footer)
        open(dst, 'wb').write(out)
        print('wrote %s: %d transitions (%d historical + %d generated)'
              % (dst, total, nhist, ngen))
    else:
        sys.stderr.write(
            'usage: generate_berlin_fat.py --all <tzdir> | '
            '<out-berlin> | <slim-berlin> <out-berlin>\n')
        sys.exit(2)


if __name__ == '__main__':
    main()
