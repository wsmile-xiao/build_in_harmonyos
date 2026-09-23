#!/usr/bin/env python3
"""Deterministic dBase III fixture generator for the dbview test_package.

The upstream dbview 1.0.4 tarball ships no test suite at all, so the consumer
tests drive the packaged binary with hand-written dBase III database files.
Every fixture is generated here from an explicit byte layout so its content is
reproducible and reviewable; `fixtures/*.dbf` are the checked-in results of
running this script with `python3 make_fixtures.py <fixtures-dir>`.

dBase III layout used below (see the upstream `dBASE` and `db_dump.header`
documents):

  32-byte header : version(1) | last update YY MM DD(3) | record count(4, LE)
                   | header size(2, LE) | record size(2, LE) | reserved(20)
  32-byte field  : name(11, NUL padded) | type(1) | data address(4)
                   | length(1) | decimal count(1) | reserved(14)
  0x0d           : header terminator
  record         : deletion flag(1: ' ' valid, '*' deleted) | field data
  0x1a           : end of file marker
"""
import os
import struct
import sys

VERSION_DBASE3 = 0x03
VERSION_DBASE3_PLUS = 0x83
VERSION_DBASE4 = 0x8B


def build(version, fields, records, update=(95, 1, 1)):
    """Assemble a .dbf image.  fields: [(name, type, length, decimals)]."""
    header_size = 32 + 32 * len(fields) + 1
    record_size = 1 + sum(f[2] for f in fields)

    head = bytearray(32)
    head[0] = version
    head[1:4] = bytes(update)
    struct.pack_into("<I", head, 4, len(records))
    struct.pack_into("<H", head, 8, header_size)
    struct.pack_into("<H", head, 10, record_size)

    out = bytearray(head)
    for offset, (name, ftype, length, decimals) in enumerate(fields):
        desc = bytearray(32)
        encoded = name.encode("ascii")
        desc[0:len(encoded)] = encoded
        desc[11] = ord(ftype)
        struct.pack_into("<I", desc, 12, offset + 1)
        desc[16] = length
        desc[17] = decimals
        out += desc
    out.append(0x0D)

    for deleted, values in records:
        out += b"*" if deleted else b" "
        for (_, ftype, length, _), value in zip(fields, values):
            raw = value.encode("ascii") if isinstance(value, str) else value
            if len(raw) > length:
                raise ValueError(f"value {value!r} does not fit in {length} bytes")
            out += raw.rjust(length) if ftype == "N" else raw.ljust(length)

    out.append(0x1A)
    return bytes(out)


def write(path, data):
    with open(path, "wb") as handle:
        handle.write(data)
    print(f"  {os.path.basename(path):24s} {len(data):5d} bytes")


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    os.makedirs(outdir, exist_ok=True)
    print(f"generating fixtures in {outdir}:")

    # 1. Plain dBase III file with a character and a numeric field.
    write(os.path.join(outdir, "basic.dbf"), build(
        VERSION_DBASE3,
        [("NAME", "C", 8, 0), ("AGE", "N", 3, 0)],
        [(False, ["ALICE", "30"]), (False, ["BOB", "7"])],
    ))

    # 2. Field types C/N/D/L and a non-zero decimal count.
    write(os.path.join(outdir, "types.dbf"), build(
        VERSION_DBASE3,
        [("ITEM", "C", 9, 0), ("QTY", "N", 4, 0), ("PRICE", "N", 8, 2),
         ("HIRED", "D", 8, 0), ("ACTIVE", "L", 1, 0)],
        [(False, ["WIDGET", "12", "199.95", "20061127", "T"]),
         (False, ["GADGET", "-3", "0.50", "19960101", "F"]),
         (False, ["DOODAD", "0", "1234.00", "        ", " "])],
    ))

    # 3. One valid, one deleted and one valid record.
    write(os.path.join(outdir, "deleted.dbf"), build(
        VERSION_DBASE3,
        [("ID", "C", 4, 0), ("VAL", "C", 6, 0)],
        [(False, ["A001", "keep"]), (True, ["A002", "gone"]), (False, ["A003", "keep2"])],
    ))

    # 4. dBase III+ version byte.
    write(os.path.join(outdir, "dbase3plus.dbf"), build(
        VERSION_DBASE3_PLUS,
        [("TAG", "C", 6, 0)],
        [(False, ["PLUS"])],
    ))

    # 5. Uppercase and underscore field names (dbview lowercases them and turns
    #    '_' into ' ' unless -r/--reserve is given).
    write(os.path.join(outdir, "names.dbf"), build(
        VERSION_DBASE3,
        [("FIRST_NAME", "C", 6, 0), ("LAST_NAME", "C", 8, 0), ("ZIP_CODE", "N", 5, 0)],
        [(False, ["ADA", "LOVELACE", "12345"])],
    ))

    # 6. Header only, no records.
    write(os.path.join(outdir, "empty.dbf"), build(
        VERSION_DBASE3,
        [("ONLY", "C", 4, 0)],
        [],
    ))

    # 7. Header announces three records but only one is present.
    truncated = build(
        VERSION_DBASE3,
        [("N", "N", 3, 0)],
        [(False, ["1"]), (False, ["2"]), (False, ["3"])],
    )
    header_size = 32 + 32 * 1 + 1
    write(os.path.join(outdir, "truncated.dbf"),
          truncated[:header_size + 1 * 4])

    # 8. Unsupported version byte.
    write(os.path.join(outdir, "badversion.dbf"), build(
        VERSION_DBASE4,
        [("X", "C", 1, 0)],
        [(False, ["X"])],
    ))


if __name__ == "__main__":
    main()
