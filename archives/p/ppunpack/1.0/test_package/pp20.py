"""Test helpers for ppunpack: a PowerPacker (PP20) encoder and an ELF reader.

ppsmall-1.0 ships no sample file, so test_package builds its PP20 inputs here.
The bitstream is the one depack.c decodes:

* file = "PP20" + 4 offset-width bytes + packed bits + 3-byte big-endian
  unpacked length + 1 byte "bits to skip";
* bits are read from the byte just before that trailer towards the start of
  the file, least significant bit first, and a value of n bits is assembled
  most significant bit first;
* output is produced from the end of the file towards the start, so the
  encoder runs an LZ77 pass over the reversed payload;
* each loop step is an optional literal run (flag 0) followed by a match; a
  match copies 2/3/4 bytes (2-bit index 0-2, offset width = table[index]) or
  5+ bytes (index 3, then a 1-bit selector for a 7-bit or table[3]-bit offset,
  then 3-bit length extensions).
"""
import struct

OFFSET_BITS = (9, 10, 12, 13)
_MAX_LEN = 5 + 7 * 30 + 6


class _Bits:
    def __init__(self):
        self.bits = []

    def put(self, value, width):
        for i in range(width - 1, -1, -1):
            self.bits.append((value >> i) & 1)


def _fits(length, dist, offset_bits):
    width = offset_bits[3] if length >= 5 else offset_bits[length - 2]
    return dist - 1 < (1 << width)


def _tokens(rev, offset_bits):
    """Greedy LZ77: ('L', bytes) literal runs and ('M', length, distance)."""
    heads, toks, lit = {}, [], bytearray()
    i, n = 0, len(rev)
    while i < n:
        best_len = best_dist = 0
        for j in reversed(heads.get(rev[i:i + 2], [])[-64:]):
            dist, length = i - j, 0
            while i + length < n and length < _MAX_LEN and rev[j + length] == rev[i + length]:
                length += 1
            while length >= 2 and not _fits(length, dist, offset_bits):
                length -= 1
            if length > best_len:
                best_len, best_dist = length, dist
        step = best_len if best_len >= 2 else 1
        for k in range(i, min(i + step, n - 1)):
            heads.setdefault(rev[k:k + 2], []).append(k)
        if best_len >= 2:
            if lit:
                toks.append(("L", bytes(lit)))
                lit = bytearray()
            toks.append(("M", best_len, best_dist))
        else:
            lit.append(rev[i])
        i += step
    if lit:
        toks.append(("L", bytes(lit)))
    return toks


def encode(data, offset_bits=OFFSET_BITS):
    """Return (pp20_bytes, stats) such that depack.c yields exactly `data`.

    stats counts the code paths used: literal runs, matches of length 2/3/4,
    and 5+ matches with the short (7-bit) and the long offset.
    """
    if not 0 < len(data) < (1 << 24):
        raise ValueError("payload size must be 1 .. 16 MiB-1")
    stats = dict.fromkeys(("lit", "m2", "m3", "m4", "m5_short", "m5_long"), 0)
    out = _Bits()
    after_literal = False
    for tok in _tokens(data[::-1], offset_bits):
        if tok[0] == "L":
            run = tok[1]
            out.put(0, 1)
            rest = len(run) - 1
            while rest >= 3:
                out.put(3, 2)
                rest -= 3
            out.put(rest, 2)
            for b in run:
                out.put(b, 8)
            stats["lit"] += 1
            after_literal = True
            continue
        _, length, dist = tok
        if not after_literal:
            out.put(1, 1)
        after_literal = False
        off = dist - 1
        if length < 5:
            out.put(length - 2, 2)
            out.put(off, offset_bits[length - 2])
            stats["m%d" % length] += 1
        else:
            out.put(3, 2)
            if off < 128:
                out.put(0, 1)
                out.put(off, 7)
                stats["m5_short"] += 1
            else:
                out.put(1, 1)
                out.put(off, offset_bits[3])
                stats["m5_long"] += 1
            rest = length - 5
            while rest >= 7:
                out.put(7, 3)
                rest -= 7
            out.put(rest, 3)
    skip = (-len(out.bits)) % 8
    stream = [0] * skip + out.bits
    body = bytearray()
    for k in range(0, len(stream), 8):
        body.append(sum(bit << pos for pos, bit in enumerate(stream[k:k + 8])))
    body.reverse()
    n = len(data)
    blob = (b"PP20" + bytes(offset_bits) + bytes(body)
            + bytes([(n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF, skip]))
    return blob, stats


def unlzw(data):
    """Decode a Unix compress(1) (.Z) stream; port of gzip's unlzw().

    Same decoder as the recipe's source(); needed here to unpack upstream's
    test data from the long ppunpack-1.0.tar.Z.
    """
    if len(data) < 3 or data[:2] != b"\x1f\x9d":
        raise ValueError("not a compress(1) stream")
    maxbits, block_mode = data[2] & 0x1F, bool(data[2] & 0x80)
    if not 9 <= maxbits <= 16:
        raise ValueError("bad max code width %d" % maxbits)
    maxmaxcode, total_bits = 1 << maxbits, len(data) * 8
    pos = group = 24
    n_bits, maxcode = 9, 511
    table = [bytes([i]) for i in range(256)] + [b""]
    free_ent = 257 if block_mode else 256
    out, old = bytearray(), None
    while True:
        if free_ent > maxcode and n_bits < maxbits:
            span = n_bits * 8
            pos = group = group + -(-(pos - group) // span) * span
            n_bits += 1
            maxcode = maxmaxcode if n_bits == maxbits else (1 << n_bits) - 1
            continue
        if pos + n_bits > total_bits:
            break
        byte, bit = divmod(pos, 8)
        code = (int.from_bytes(data[byte:byte + 3], "little") >> bit) & ((1 << n_bits) - 1)
        pos += n_bits
        if old is None:
            if code >= 256:
                raise ValueError("corrupt first code")
            out += table[code]
            old = code
            continue
        if code == 256 and block_mode:
            span = n_bits * 8
            pos = group = group + -(-(pos - group) // span) * span
            del table[257:]
            free_ent, n_bits, maxcode = 256, 9, 511
            continue
        if code < len(table):
            entry = table[code]
        elif code == free_ent:
            entry = table[old] + table[old][:1]
        else:
            raise ValueError("corrupt code %d" % code)
        out += entry
        if free_ent < maxmaxcode:
            new = table[old] + entry[:1]
            if free_ent < len(table):
                table[free_ent] = new
            else:
                table.append(new)
            free_ent += 1
        old = code
    return bytes(out)


def elf_facts(path):
    """Header facts of an ELF64 LE file plus the owners of its PT_NOTE notes."""
    with open(path, "rb") as handle:
        img = handle.read()
    if img[:4] != b"\x7fELF":
        return {"elf": False}
    facts = {"elf": True, "class64": img[4] == 2, "le": img[5] == 1}
    if not (facts["class64"] and facts["le"]):
        return facts
    e_type, e_machine = struct.unpack_from("<HH", img, 16)
    e_phoff, = struct.unpack_from("<Q", img, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", img, 54)
    facts.update(e_type=e_type, e_machine=e_machine, interp=None, note_owners=[])
    for i in range(e_phnum):
        p_type, _, p_offset, _, _, p_filesz, _, p_align = struct.unpack_from(
            "<IIQQQQQQ", img, e_phoff + i * e_phentsize)
        seg = img[p_offset:p_offset + p_filesz]
        if p_type == 3:                                   # PT_INTERP
            facts["interp"] = seg.rstrip(b"\0").decode("ascii", "replace")
        elif p_type == 4:                                 # PT_NOTE
            pad = 7 if p_align == 8 else 3
            off = 0
            while off + 12 <= len(seg):
                namesz, descsz, _ = struct.unpack_from("<III", seg, off)
                name = seg[off + 12:off + 12 + namesz].rstrip(b"\0")
                facts["note_owners"].append(name.decode("ascii", "replace"))
                desc_off = (off + 12 + namesz + pad) & ~pad
                off = (desc_off + descsz + pad) & ~pad
    return facts
