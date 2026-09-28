#!/usr/bin/env python3
"""Functional checks for the packaged lbrate binary (stdlib only).

Run by test_package/conanfile.py as::

    python3 test_lbrate.py --bin <package>/bin/lbrate --workdir <build folder>

The upstream distribution has no tests and no test data, so this script builds
spec-valid CP/M LBR archives on the fly and drives the real binary against
them:

* a directory sector (first entry = the directory itself, 11 blank name bytes),
* ``HELLO.TXT``  -- a stored member with CRC-16 and CP/M creation/modification
  date stamps,
* ``SQUEEZE.TQT`` -- a squeezed member (Huffman + 0x90 RLE, magic 0xFF76) whose
  embedded original name is ``SQUEEZE.TXT``; the encoder below is the inverse
  of upstream readhuff.c/readrle.c.

OHOS-specific checks (see MANIFEST.yml):

* OHOS-1 ELF contract of the delivered binary: 64-bit AArch64, PIE (ET_DYN),
  PT_INTERP = /lib/ld-musl-aarch64.so.1 (the OHOS musl loader).  Pure file
  inspection, so it also runs on non-aarch64 hosts.
* OHOS-2 timestamp restoration: lbrate turns the CP/M date/time into time_t
  with the libc gmtime()/mktime() pair under TZ=UTC0 and applies it with
  utime(); the extracted files' mtime on the OHOS file system must equal the
  exact epoch computed here (modification date by default, creation date
  with -c).

Execution policy: every runtime case needs the binary to execute.  On an
aarch64 host a failing start-up probe is a hard failure.  Only on a
non-aarch64 host (an x86_64 build runner, where the dynamic OHOS binary cannot
load its musl loader) are the runtime cases reported as SKIP -- never as
passed.
"""
import argparse
import calendar
import datetime
import heapq
import os
import platform
import struct
import subprocess
import sys
from collections import Counter

SECTOR = 128
CPM_EOF = 0x1A
MAGIC_SQ = 0xFF76
OHOS_LOADER = "/lib/ld-musl-aarch64.so.1"

HELLO = b"lbrate stored member payload 0123456789\r\nsecond line\r\n"
SQUEEZED = (b"lbrate squeezed member: "
            + b"A" * 40
            + b" end of run\r\nHuffman+RLE decode check abcdefghijklmnopqrstuvwxyz\r\n")

# CP/M timestamps (lbrate 1.1 was released in 2001)
HELLO_M = (2001, 6, 15, 12, 34, 56)
HELLO_C = (1999, 12, 31, 23, 58, 0)
SQUEEZE_M = (2000, 2, 29, 8, 0, 30)     # leap day


# ── archive construction ─────────────────────────────────────────────────

def crc16(data):
    """CRC-16/XMODEM (poly 0x1021, init 0) -- the table in main.c calc_crc()."""
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def cpm_date(y, m, d):
    """Days since 31 Dec 1977 (day 1 = 1 Jan 1978)."""
    return (datetime.date(y, m, d) - datetime.date(1977, 12, 31)).days


def cpm_time(h, mi, s):
    return (h << 11) | (mi << 5) | (s // 2)


def pad(data):
    size = -(-len(data) // SECTOR) * SECTOR
    return data + bytes([CPM_EOF]) * (size - len(data))


def rle_encode(payload):
    """Inverse of readrle.c: runs >= 3 become <byte> 0x90 <count>."""
    out, i = [], 0
    while i < len(payload):
        b = payload[i]
        if b == 0x90:
            out += [0x90, 0]
            i += 1
            continue
        run = 1
        while i + run < len(payload) and payload[i + run] == b and run < 255:
            run += 1
        if run >= 3:
            out += [b, 0x90, run]
            i += run
        else:
            out.append(b)
            i += 1
    return out


def squeeze(payload, orig_name):
    """Build a squeezed file in the layout readhuff.c convert_huff() reads."""
    syms = rle_encode(payload) + [256]          # 256 = Huffman EOF
    heap = [(n, i, s) for i, (s, n) in enumerate(sorted(Counter(syms).items()))]
    heapq.heapify(heap)
    tick = len(heap)
    while len(heap) > 1:
        n0, _, a = heapq.heappop(heap)
        n1, _, b = heapq.heappop(heap)
        heapq.heappush(heap, (n0 + n1, tick, (a, b)))
        tick += 1
    root = heap[0][2]

    # Lay the tree out breadth-first so the root is node 0.
    nodes, codes, queue = [], {}, [(root, [])]
    index = {id(root): 0}
    while queue:
        node, path = queue.pop(0)
        kids = []
        for bit, child in enumerate(node):
            if isinstance(child, tuple):
                index[id(child)] = len(index)
                queue.append((child, path + [bit]))
                kids.append(index[id(child)])
            else:
                codes[child] = path + [bit]
                kids.append(child ^ 0xFFFF)     # leaf: VALUE_CONV()
        nodes.append(kids)

    bits = [bit for s in syms for bit in codes[s]]
    stream = bytearray()
    for i in range(0, len(bits), 8):            # bit_input() reads LSB first
        stream.append(sum(bit << j for j, bit in enumerate(bits[i:i + 8])))

    header = struct.pack("<HH", MAGIC_SQ, sum(payload) & 0xFFFF)
    header += orig_name.encode("ascii") + b"\0"
    header += struct.pack("<H", len(nodes))
    header += b"".join(struct.pack("<HH", k0, k1) for k0, k1 in nodes)
    return header + bytes(stream)


def dir_entry(status, name83, pos, sectors, crc, c=None, m=None):
    cd = cpm_date(*c[:3]) if c else 0
    ct = cpm_time(*c[3:]) if c else 0
    md = cpm_date(*m[:3]) if m else 0
    mt = cpm_time(*m[3:]) if m else 0
    entry = bytes([status]) + name83.encode("ascii")
    entry += struct.pack("<7H", pos, sectors, crc, cd, md, ct, mt) + bytes(6)
    assert len(entry) == 32, len(entry)
    return entry


def build_lbr(members):
    """members: list of (name83, raw bytes, creation, modification)."""
    n_entries = 1 + len(members)
    dir_sectors = -(-n_entries // 4)
    entries, blobs, pos = [], [], dir_sectors
    for name83, raw, c, m in members:
        data = pad(raw)
        sectors = len(data) // SECTOR
        entries.append(dir_entry(0, name83, pos, sectors, crc16(data), c, m))
        blobs.append(data)
        pos += sectors
    head = dir_entry(0, " " * 11, 0, dir_sectors, 0)
    unused = dir_entry(0xFF, " " * 11, 0, 0, 0) * (dir_sectors * 4 - n_entries)
    return head + b"".join(entries) + unused + b"".join(blobs)


# ── checks ───────────────────────────────────────────────────────────────

class Runner:
    def __init__(self):
        self.passed = self.failed = self.skipped = 0

    def ok(self, case, msg):
        self.passed += 1
        print("ok   [{}] {}".format(case, msg))

    def fail(self, case, msg):
        self.failed += 1
        print("FAIL [{}] {}".format(case, msg))

    def check(self, case, cond, msg, detail=""):
        if cond:
            self.ok(case, msg)
        else:
            self.fail(case, "{} -- {}".format(msg, detail))

    def skip(self, case, msg):
        self.skipped += 1
        print("SKIP [{}] {}".format(case, msg))


def elf_contract(path):
    """Return (ok, detail) for the OHOS AArch64 PIE + musl loader contract."""
    with open(path, "rb") as f:
        blob = f.read()
    if blob[:4] != b"\x7fELF" or blob[4] != 2 or blob[5] != 1:
        return False, "not a 64-bit little-endian ELF"
    e_type, e_machine = struct.unpack_from("<HH", blob, 16)
    e_phoff, = struct.unpack_from("<Q", blob, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", blob, 54)
    interp = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", blob, off)
        if p_type == 3:                           # PT_INTERP
            p_offset, = struct.unpack_from("<Q", blob, off + 8)
            p_filesz, = struct.unpack_from("<Q", blob, off + 32)
            interp = blob[p_offset:p_offset + p_filesz].rstrip(b"\0").decode()
    detail = "e_machine={} e_type={} interp={}".format(e_machine, e_type, interp)
    return (e_machine == 183 and e_type == 3 and interp == OHOS_LOADER), detail


def run(binary, args, cwd):
    env = dict(os.environ, TZ="UTC0")
    proc = subprocess.run([binary] + args, cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("latin-1"), proc.stderr.decode("latin-1")


def read(path):
    with open(path, "rb") as f:
        return f.read()


def runtime_cases(t, binary, work):
    good = os.path.join(work, "good.lbr")
    sq = squeeze(SQUEEZED, "SQUEEZE.TXT")
    archive = build_lbr([("HELLO   TXT", HELLO, HELLO_C, HELLO_M),
                         ("SQUEEZE TQT", sq, None, SQUEEZE_M)])
    with open(good, "wb") as f:
        f.write(archive)
    bad = bytearray(archive)
    bad[SECTOR + 3] ^= 0xFF                       # corrupt HELLO.TXT data
    with open(os.path.join(work, "bad.lbr"), "wb") as f:
        f.write(bytes(bad))

    rc, out, err = run(binary, ["-h"], work)
    t.check("R1", rc == 0 and "lbrate 1.1" in out, "-h prints the 1.1 usage banner",
            "rc={} out={!r}".format(rc, out[:80]))

    rc, out, err = run(binary, ["-z", "good.lbr"], work)
    t.check("R2", rc == 1 and "option `z' not recognised" in err,
            "unknown option rejected via libc getopt()/optopt",
            "rc={} err={!r}".format(rc, err))

    rc, out, err = run(binary, ["-l", "good.lbr"], work)
    lines = out.splitlines()
    t.check("R3", rc == 0 and len(lines) == 2
            and lines[0].split()[:2] == ["hello.txt", "128"]
            and "2001-06-15 12:34" in lines[0]
            and lines[1].split()[0] == "squeeze.txt"
            and "2000-02-29 08:00" in lines[1],
            "-l lists both members with sizes and CP/M dates",
            repr(out))

    rc, out, err = run(binary, ["-l", "good.lbr", "sq*"], work)
    t.check("R4", rc == 0 and out.split() and out.split()[0] == "squeeze.txt"
            and "hello" not in out,
            "wildcard 'sq*' selects only the squeezed member", repr(out))

    rc, out, err = run(binary, ["-t", "good.lbr"], work)
    t.check("R5", rc == 0 and out.count("ok") == 2 and "failed" not in out,
            "-t verifies both member CRCs", "rc={} out={!r}".format(rc, out))

    rc, out, err = run(binary, ["-t", "bad.lbr"], work)
    t.check("R6", rc == 1 and "bad CRC" in out,
            "-t on a corrupted member reports 'bad CRC' and exits 1",
            "rc={} out={!r}".format(rc, out))

    ext = os.path.join(work, "extract")
    os.makedirs(ext, exist_ok=True)
    rc, out, err = run(binary, [good], ext)
    t.check("R7", rc == 0 and os.path.isfile(os.path.join(ext, "hello.txt"))
            and read(os.path.join(ext, "hello.txt")) == pad(HELLO),
            "stored member extracted byte-for-byte (128-byte CP/M record, ^Z padded)",
            "rc={} out={!r}".format(rc, out))
    t.check("R8", os.path.isfile(os.path.join(ext, "squeeze.txt"))
            and read(os.path.join(ext, "squeeze.txt")) == SQUEEZED,
            "squeezed member decoded (Huffman+RLE) and renamed to its original name",
            "files={}".format(sorted(os.listdir(ext))))

    want_m = calendar.timegm(HELLO_M)
    want_sq = calendar.timegm(SQUEEZE_M)
    got_m = int(os.stat(os.path.join(ext, "hello.txt")).st_mtime)
    got_sq = int(os.stat(os.path.join(ext, "squeeze.txt")).st_mtime)
    t.check("OHOS-2a", got_m == want_m and got_sq == want_sq,
            "utime() restored CP/M modification stamps (TZ=UTC0)",
            "hello {} want {}, squeeze {} want {}".format(got_m, want_m, got_sq, want_sq))

    extc = os.path.join(work, "extract_c")
    os.makedirs(extc, exist_ok=True)
    rc, out, err = run(binary, ["-c", good, "hello.txt"], extc)
    want_c = calendar.timegm(HELLO_C)
    got_c = (int(os.stat(os.path.join(extc, "hello.txt")).st_mtime)
             if os.path.isfile(os.path.join(extc, "hello.txt")) else None)
    t.check("OHOS-2b", rc == 0 and got_c == want_c,
            "-c restores the CP/M creation stamp instead",
            "rc={} got {} want {}".format(rc, got_c, want_c))

    extn = os.path.join(work, "extract_n")
    os.makedirs(extn, exist_ok=True)
    rc, out, err = run(binary, ["-n", good], extn)
    t.check("R9", rc == 0 and os.path.isfile(os.path.join(extn, "squeeze.tqt"))
            and read(os.path.join(extn, "squeeze.tqt")) == pad(sq),
            "-n extracts the squeezed member raw under its LBR name",
            "rc={} files={}".format(rc, sorted(os.listdir(extn))))


RUNTIME_CASES = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "OHOS-2a", "OHOS-2b", "R9")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True, help="path to the lbrate executable")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--runtime-only", action="store_true",
                    help="skip the ELF contract (for a statically relinked local copy)")
    args = ap.parse_args()

    binary = os.path.abspath(args.bin)
    work = os.path.abspath(args.workdir)
    os.makedirs(work, exist_ok=True)
    t = Runner()

    if not args.runtime_only:
        ok, detail = elf_contract(binary)
        t.check("OHOS-1", ok, "ELF: AArch64 PIE with the OHOS musl loader " + OHOS_LOADER, detail)

    machine = platform.machine().lower()
    try:
        probe = subprocess.run([binary, "-h"], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE).returncode
    except OSError as exc:
        probe = exc
    if probe != 0 and machine not in ("aarch64", "arm64"):
        for case in RUNTIME_CASES:
            t.skip(case, "host {} cannot execute the aarch64 OHOS binary (probe: {})"
                   .format(machine, probe))
    else:
        runtime_cases(t, binary, work)

    print("lbrate test_package: passed={} failed={} skipped={}"
          .format(t.passed, t.failed, t.skipped))
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
