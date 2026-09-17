#!/usr/bin/env python3
"""Consumer-side check for the packaged hwdata 0.411 (R34: real data + .pc).

This is not a smoke test: it parses the shipped databases and verifies the
pkg-config contract that consumers such as libdisplay-info rely on
(meson `dependency('hwdata')` -> `pkgdatadir` -> `pnp.ids`).

Usage: test_hwdata.py <share/hwdata dir> <path/to/hwdata.pc>
"""
import os
import re
import sys

data_dir = sys.argv[1] if len(sys.argv) > 1 else ""
pc_path = sys.argv[2] if len(sys.argv) > 2 else ""

# ── 1. all upstream IDFILES are shipped ─────────────────────────────────────
expected = ("pci.ids", "usb.ids", "oui.txt", "iab.txt", "pnp.ids")
for name in expected:
    path = os.path.join(data_dir, name)
    assert os.path.isfile(path), f"missing data file: {path}"
    assert os.path.getsize(path) > 1000, f"suspiciously small: {path}"

# ── 2. pnp.ids parses as `<PNP_ID>\t<Vendor>` records ───────────────────────
pnp = os.path.join(data_dir, "pnp.ids")
records = {}
with open(pnp, encoding="utf-8") as fh:
    for line in fh:
        if not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        assert len(parts) >= 2, f"pnp.ids malformed record: {line!r}"
        assert parts[0].strip() and parts[1].strip(), f"empty field: {line!r}"
        records[parts[0].strip()] = parts[1].strip()
assert len(records) > 1000, f"pnp.ids too few records: {len(records)}"
# A stable, real entry (AAA = Avolites Ltd) — proves this is the real db,
# not an empty placeholder.
assert "AAA" in records, "pnputils: well-known PNP id AAA absent"
assert records["AAA"].strip(), "pnputils: AAA has no vendor name"

# ── 3. pci.ids / usb.ids are the real databases ─────────────────────────────
with open(os.path.join(data_dir, "pci.ids"), encoding="utf-8") as fh:
    pci = fh.read()
assert re.search(r"^#.*\bDate:", pci, re.M), "pci.ids: no Date: header"
assert re.search(r"^[0-9a-f]{4}\s+\S", pci, re.M), "pci.ids: no vendor records"

with open(os.path.join(data_dir, "usb.ids"), encoding="utf-8") as fh:
    usb = fh.read()
assert re.search(r"^#.*\bDate:", usb, re.M), "usb.ids: no Date: header"
assert re.search(r"^[0-9a-f]{4}\s+\S", usb, re.M), "usb.ids: no vendor records"

# ── 4. hwdata.pc contract (what libdisplay-info's meson consumes) ───────────
assert os.path.isfile(pc_path), f"hwdata.pc missing: {pc_path}"
with open(pc_path, encoding="utf-8") as fh:
    pc = fh.read()
for field in ("Name:", "Description:", "Version:", "prefix=", "pkgdatadir="):
    assert re.search(rf"^{re.escape(field)}", pc, re.M), f"hwdata.pc missing {field}"
assert re.search(r"^Name:\s*hwdata\s*$", pc, re.M), "hwdata.pc: wrong Name"
assert "0.411" in pc, "hwdata.pc: version does not match the packaged release"

# pkgdatadir must point at the directory that actually holds pnp.ids
m = re.search(r"^pkgdatadir=(.+)$", pc, re.M)
assert m, "hwdata.pc: pkgdatadir not parseable"
declared = m.group(1).strip()
assert os.path.isdir(declared), f"hwdata.pc pkgdatadir does not exist: {declared}"
assert os.path.isfile(os.path.join(declared, "pnp.ids")), \
    f"hwdata.pc pkgdatadir lacks pnp.ids: {declared}"

print(f"hwdata 0.411 consumer API: PASS "
      f"({len(records)} pnp.ids records, pkgdatadir={declared})")
