"""Build a minimal, structurally valid SF2 (SoundFont) fixture for sftovkb.

sftovkb walks only the preset header list, but vkeybd's parser is strict about
record sizes, so the fixture matches what sffile.c actually reads:

  * ``phdr`` -> ``npresets = size / 38``  (20 name + 2 preset + 2 bank
    + 2 bagNdx + 4 lib + 4 genre + 4 morph)
  * ``inst`` -> ``ninsts  = size / 22``  (20 name + 2 bagNdx)
  * ``shdr`` -> 46 bytes per sample record

phdr/pbag/pmod/pgen and inst/ibag/imod/igen are terminal-terminated lists, so
each carries one extra all-zero entry. Because sftovkb prints
``range(npresets - 1)``, the terminal EOP record is intentionally *not* printed;
the fixture therefore declares N+1 phdr records to have N presets appear.
"""

import struct
import sys

PHDR_SIZE = 38
INST_SIZE = 22
SHDR_SIZE = 46


def _chunk(cid, payload):
    """RIFF chunk: 4-byte id + little-endian uint32 size + payload."""
    return cid + struct.pack("<I", len(payload)) + payload


def _pad16(data):
    """RIFF chunks are word-aligned; pad to an even length."""
    return data + (b"\x00" if len(data) % 2 else b"")


def _name20(text):
    raw = text.encode("ascii")[:20]
    return raw + b" " * (20 - len(raw))


def _phdr_record(name, preset, bank, bag):
    return _name20(name) + struct.pack("<HHHiii", preset, bank, bag, 0, 0, 0)


def _inst_record(name, bag):
    return _name20(name) + struct.pack("<H", bag)


def _shdr_record(name):
    return (_name20(name) + struct.pack("<iiii", 0, 0, 0, 0)
            + struct.pack("<iBBHHH", 0, 0, 0, 0, 0, 0) + struct.pack("<H", 0))


def build_sf2(preset_names, bank=0):
    """Build an SF2 whose preset list is exactly ``preset_names`` when printed.

    A terminal EOP record is appended, and sftovkb drops the last entry, so
    ``len(preset_names)`` records plus one terminal yields the requested list.
    """
    n = len(preset_names)

    phdr = b"".join(_phdr_record(name, i, bank, i) for i, name in enumerate(preset_names))
    phdr += _phdr_record("EOP", 0, 0, n)  # terminal

    npbags = n + 1
    pbag = b"".join(struct.pack("<H", 0) for _ in range(npbags))
    pmod = b"".join(struct.pack("<HH", 0, 0) for _ in range(npbags))
    pgen = b"".join(struct.pack("<hh", 0, 0) for _ in range(npbags)) + struct.pack("<hh", 0, 0)

    inst = _inst_record("Instrument", 0) + _inst_record("EOI", 1)
    nibags = 2
    ibag = b"".join(struct.pack("<H", 0) for _ in range(nibags))
    imod = b"".join(struct.pack("<HH", 0, 0) for _ in range(nibags))
    igen = b"".join(struct.pack("<hh", 0, 0) for _ in range(nibags)) + struct.pack("<hh", 0, 0)

    shdr = _shdr_record("sample") + _shdr_record("EOS")

    # Order matters: sffile.c dispatches on chunk id as it walks the list.
    pdta = (_chunk(b"phdr", _pad16(phdr)) + _chunk(b"pbag", _pad16(pbag))
            + _chunk(b"pmod", _pad16(pmod)) + _chunk(b"pgen", _pad16(pgen))
            + _chunk(b"inst", _pad16(inst)) + _chunk(b"ibag", _pad16(ibag))
            + _chunk(b"imod", _pad16(imod)) + _chunk(b"igen", _pad16(igen))
            + _chunk(b"shdr", _pad16(shdr)))
    pdta_list = _chunk(b"LIST", b"pdta" + pdta)

    ifil = _chunk(b"ifil", struct.pack("<HH", 2, 1))
    iver = _chunk(b"iver", struct.pack("<IH", 0x00020100, 1))
    inam = _chunk(b"inam", _pad16(b"vkeybd conan test fixture"))
    info_list = _chunk(b"LIST", b"INFO" + ifil + iver + inam)

    assert len(phdr) % PHDR_SIZE == 0, len(phdr)
    assert len(inst) % INST_SIZE == 0, len(inst)
    return _chunk(b"RIFF", b"sfbk" + info_list + pdta_list)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "fixture.sf2"
    # Names chosen to exercise sftovkb's own sanitiser in sftovkb.c: braces are
    # replaced by spaces, and square brackets by parentheses.
    names = ["Piano", "Brass [Ensemble]", "Chord {Pad}"]
    data = build_sf2(names)
    with open(out, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes, %d presets)" % (out, len(data), len(names)))


if __name__ == "__main__":
    main()
