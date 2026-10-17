#!/usr/bin/env python3
"""Consumer tests for the packaged smem 1.5 deliverables.

smem 1.5 ships two programs and no test suite of its own, so this file is the
whole functional contract:

* ``smem``    — the Python 3 reporting front end
* ``smemcap`` — the C capture helper that walks /proc into a tar archive

The tests are grouped as follows.

A. Artifact / target checks — the two executables exist, carry the exec bit,
   and ``smemcap`` really is an AArch64 OHOS ELF rather than a host build.
   These are pure file inspections, so they run identically on an x86_64
   developer box and on the AArch64 OHOS worker.

B. Synthetic ``--source`` battery — a capture archive is synthesised byte for
   byte in the layout ``smemcap.c`` writes (512-byte header, octal fields,
   checksum at 148, typeflag at 156, plus the ``<pid>`` directory members), with
   smaps figures chosen so every reported number can be computed by hand.  The
   packaged ``smem`` is then driven against it and each number is checked
   against the independently computed expectation.  Because ``smem`` is a
   platform independent script this battery is deterministic everywhere.

C. Live capture — on an AArch64 build machine the delivered ``smemcap`` binary
   is executed for real, its archive is validated with an independent reader,
   and the result is fed back through ``smem --source``.

Usage: test_smem.py <package-bin-dir>
"""
import io
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile

PASSED = 0
FAILED = 0


def check(ok, label, detail=""):
    global PASSED, FAILED
    suffix = (" — " + detail) if detail else ""
    if ok:
        PASSED += 1
        print("OK   %s%s" % (label, suffix))
    else:
        FAILED += 1
        print("FAIL %s%s" % (label, suffix))


# ───────────────────────────── ELF inspection ──────────────────────────────

EM_AARCH64 = 183
PT_INTERP = 3


def elf_facts(path):
    """Parse the ELF header/program headers without any external tooling."""
    with open(path, "rb") as handle:
        data = handle.read()
    facts = {"magic": data[:4], "class": data[4], "data": data[5]}
    if facts["magic"] != b"\x7fELF":
        return facts
    end = "<" if data[5] == 1 else ">"
    facts["type"] = struct.unpack(end + "H", data[16:18])[0]
    facts["machine"] = struct.unpack(end + "H", data[18:20])[0]
    phoff = struct.unpack(end + "Q", data[32:40])[0]
    phentsize = struct.unpack(end + "H", data[54:56])[0]
    phnum = struct.unpack(end + "H", data[56:58])[0]
    interp = None
    for index in range(phnum):
        off = phoff + index * phentsize
        if struct.unpack(end + "I", data[off:off + 4])[0] == PT_INTERP:
            p_offset = struct.unpack(end + "Q", data[off + 8:off + 16])[0]
            p_filesz = struct.unpack(end + "Q", data[off + 32:off + 40])[0]
            interp = data[p_offset:p_offset + p_filesz].rstrip(b"\0").decode("utf-8", "replace")
    facts["interp"] = interp
    return facts


# ───────────────── smemcap archive writer (mirrors smemcap.c) ──────────────

def cap_header(path, mode, uid, gid, size, mtime, kind):
    """Byte-for-byte reimplementation of smemcap.c:writeheader()."""
    header = bytearray(512)
    name = path.encode()
    assert len(name) < 100, path
    header[0:len(name)] = name

    def put(offset, width, value):
        # Pad to the exact slice width: assigning fewer bytes than the slice
        # holds would shrink the bytearray and shift every later field.
        field = ("%0*o" % (width - 1, value)).encode() + b"\0"
        header[offset:offset + width] = field.ljust(width, b"\0")[:width]

    put(100, 8, mode & 0o777)
    put(108, 8, uid)
    put(116, 8, gid)
    put(124, 12, size)
    put(136, 12, mtime)
    # eight placeholder spaces followed by the one character typeflag
    header[148:157] = b"        " + str(kind).encode()
    # smemcap sums the whole 512-byte block while the checksum field still
    # holds its eight placeholder spaces, which is exactly the tar rule
    # ("treat the checksum field as spaces"), so the raw sum is the value.
    # It rewrites that field with "%06o", i.e. 6 digits + NUL, which leaves the
    # eighth field byte holding the placeholder space — hence width 7 here.
    put(148, 7, sum(header))
    assert len(header) == 512
    return bytes(header)


def cap_archive(path):
    """Write a capture archive in smemcap's on-the-wire format."""
    with open(path, "wb") as out:
        for name, mode, uid, gid, kind, payload in CAPTURE:
            out.write(cap_header(name, mode, uid, gid, len(payload), 0, kind))
            if payload:
                out.write(payload)
                pad = (-len(payload)) % 512
                if pad:
                    out.write(b"\0" * pad)


# ───────────────────────── synthetic /proc fixture ─────────────────────────

MEMINFO = b"""MemTotal:       16307720 kB
MemFree:         2097152 kB
MemAvailable:    8388608 kB
Buffers:          262144 kB
Cached:          4194304 kB
SwapCached:       131072 kB
Active:          5242880 kB
Inactive:        2097152 kB
SwapTotal:       4194304 kB
SwapFree:        4194304 kB
AnonPages:       6291456 kB
Mapped:           524288 kB
SReclaimable:     262144 kB
"""

VERSION = b"Linux version 5.10.0 (synthetic smem fixture)\n"


def mapping(addr, perms, offset, dev, inode, name, size, rss, pss,
            shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=0,
            referenced=0, swap=0):
    """Render one /proc/<pid>/smaps record with upstream's field set."""
    header = "%s %s %s %s %d" % (addr, perms, offset, dev, inode)
    if name:
        header += " " + name
    lines = [header]
    for key, value in (("Size", size), ("Rss", rss), ("Pss", pss),
                       ("Shared_Clean", shared_clean), ("Shared_Dirty", shared_dirty),
                       ("Private_Clean", private_clean), ("Private_Dirty", private_dirty),
                       ("Referenced", referenced), ("Anonymous", 0), ("Swap", swap)):
        lines.append("%s: %d kB" % (key, value))
    return ("\n".join(lines) + "\n").encode()


# pid 1000 "thing", uid/gid 1000 "tester" — 4 mappings
#   anon  size 4  rss 4  pss 2  shared_clean 2 private_clean 2
#   /lib/thing    size 4 rss 4  pss 1  shared_clean 1
#   [heap]        size 4  rss 12 pss 12 private_dirty 12
#   anon  size 4  rss 3  pss 3  private_dirty 3  swap 7
MAPS_1000 = b"".join([
    mapping("1000-2000", "rw-p", "00000000", "00:00", 0, "",
            4, 4, 2, shared_clean=2, private_clean=2, referenced=4),
    mapping("2000-3000", "r--p", "00000000", "fd:00", 123456, "/lib/thing",
            4, 4, 1, shared_clean=1),
    mapping("3000-4000", "rw-p", "00000000", "00:00", 0, "[heap]",
            4, 12, 12, private_dirty=12),
    mapping("4000-5000", "rw-p", "00000000", "00:00", 0, "",
            4, 3, 3, private_dirty=3, swap=7),
])

# pid 1001 "other", uid/gid 0 "root" — 2 mappings
#   anon      size 8 rss 6 pss 6 private_clean 1 private_dirty 5
#   [anon:other] size 8 rss 2 pss 2
MAPS_1001 = b"".join([
    mapping("5000-6000", "rw-p", "00000000", "00:00", 0, "",
            8, 6, 6, private_clean=1, private_dirty=5),
    mapping("6000-7000", "r-xp", "00000000", "00:00", 0, "[anon:other]",
            8, 2, 2),
])

STAT_1000 = (b"1000 (thing) S 1 1000 1000 0 -1 4194304 100 0 0 0 "
             b"1 2 0 0 20 0 1 0 100 0 0\n")
STAT_1001 = (b"1001 (other) S 1 0 0 0 -1 4194304 100 0 0 0 "
             b"1 2 0 0 20 0 1 0 100 0 0\n")

# name, mode, uid, gid, typeflag, payload — the exact member sequence smemcap
# produces: meminfo, version, then <pid>/ (directory) + smaps + cmdline + stat.
CAPTURE = [
    ("meminfo", 0o644, 0, 0, "0", MEMINFO),
    ("version", 0o644, 0, 0, "0", VERSION),
    ("1000", 0o555, 1000, 1000, "5", b""),
    ("1000/smaps", 0o644, 1000, 1000, "0", MAPS_1000),
    ("1000/cmdline", 0o644, 1000, 1000, "0", b"/usr/bin/thing\0--serve\0"),
    ("1000/stat", 0o644, 1000, 1000, "0", STAT_1000),
    ("1001", 0o555, 0, 0, "5", b""),
    ("1001/smaps", 0o644, 0, 0, "0", MAPS_1001),
    ("1001/cmdline", 0o644, 0, 0, "0", b"/usr/bin/other\0"),
    ("1001/stat", 0o644, 0, 0, "0", STAT_1001),
]

# ─────────────────────── independently computed fixtures ───────────────────
# smemcap writes only the numeric uid/gid into the capture headers, never the
# uname/gname fields, so `smem --source` resolves owners numerically — verified
# against a real smemcap archive (`uname=''` on the <pid> directory member).
EXPECTED = {
    1000: {"name": "thing", "user": "1000", "command": "/usr/bin/thing --serve",
           "maps": 4, "swap": 7, "uss": 17, "pss": 18, "rss": 23, "vss": 16},
    1001: {"name": "other", "user": "0", "command": "/usr/bin/other",
           "maps": 2, "swap": 0, "uss": 6, "pss": 8, "rss": 8, "vss": 16},
}
TOTALS = {"swap": 7, "uss": 23, "pss": 26, "rss": 31, "vss": 32}
EXPECTED_MAPS = {
    "<anonymous>": {"pids": 2, "count": 3, "pss": 11, "rss": 13, "swap": 7,
                    "avgpss": 5, "uss": 11},
    "/lib/thing": {"pids": 1, "count": 1, "pss": 1, "rss": 4, "swap": 0,
                   "avgpss": 1, "uss": 0},
    "[heap]": {"pids": 1, "count": 1, "pss": 12, "rss": 12, "swap": 0,
               "avgpss": 12, "uss": 12},
    "[anon:other]": {"pids": 1, "count": 1, "pss": 2, "rss": 2, "swap": 0,
                     "avgpss": 2, "uss": 0},
}
EXPECTED_USERS = {
    "1000": {"count": 1, "swap": 7, "uss": 17, "pss": 18, "rss": 23},
    "0": {"count": 1, "swap": 0, "uss": 6, "pss": 8, "rss": 8},
}
EXPECTED_SYSTEM = {
    "firmware/hardware": (0, 0, 0),
    "kernel image": (0, 0, 0),
    "kernel dynamic memory": (7394824, 4194304, 3200520),
    "userspace memory": (6815744, 524288, 6291456),
    "free memory": (2097152, 2097152, 0),
}


# ──────────────────────────────── helpers ──────────────────────────────────

def run(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, **kwargs)


def keyed_rows(text):
    """Index smem table rows by their first cell, keeping the full cell list.

    Every caller asks for a header, so the first emitted line is skipped.
    smem pads each column to a fixed width, so a value may itself contain
    spaces (``command``, ``map``, ``area``); callers therefore read the
    rightmost numeric cells off the end of a row.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    out = {}
    for line in lines[1:]:
        if line.startswith("---"):
            continue
        cells = line.split()
        out.setdefault(cells[0], cells)
    return out


def data_lines(text):
    """smem output lines that are neither blank, the header nor the totals rule."""
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip())
    except StopIteration:
        return []
    body = lines[start + 1:]
    return [ln for ln in body if ln.strip() and not ln.startswith("---")]


def totals_line(text):
    """The row smem -t prints after its dashed rule, or None."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("---") and index + 1 < len(lines):
            return lines[index + 1]
    return None


def smem(smem_bin, archive, *args):
    return run([sys.executable, smem_bin, "-S", archive] + list(args))


# ─────────────────────────── A. artifact checks ─────────────────────────────

def test_artifacts(bindir):
    print("\n== A. artifacts and OHOS target ==")
    smem_bin = os.path.join(bindir, "smem")
    cap_bin = os.path.join(bindir, "smemcap")

    for path, label in ((smem_bin, "smem"), (cap_bin, "smemcap")):
        check(os.path.isfile(path), "%s present in package bin/" % label, path)
        check(os.access(path, os.X_OK), "%s carries the exec bit" % label)

    with open(smem_bin, "rb") as handle:
        first = handle.readline().decode("utf-8", "replace").strip()
    check(first == "#!/usr/bin/env python3",
          "smem shebang targets python3", first)

    source = open(smem_bin, "rb").read()
    try:
        compile(source, "smem", "exec")
        check(True, "packaged smem parses as Python 3")
    except SyntaxError as exc:
        check(False, "packaged smem parses as Python 3", str(exc))

    facts = elf_facts(cap_bin)
    check(facts.get("magic") == b"\x7fELF", "smemcap is an ELF object",
          repr(facts.get("magic")))
    check(facts.get("class") == 2, "smemcap is ELF64", "class=%s" % facts.get("class"))
    check(facts.get("machine") == EM_AARCH64,
          "smemcap targets AArch64 (OHOS PC arm64)",
          "e_machine=%s" % facts.get("machine"))
    interp = facts.get("interp")
    check(bool(interp) and "aarch64" in interp,
          "smemcap is loaded by the AArch64 platform loader", str(interp))

    man = os.path.join(os.path.dirname(bindir), "share", "man", "man8", "smem.8")
    check(os.path.isfile(man), "upstream man page installed", man)
    lic = os.path.join(os.path.dirname(bindir), "licenses", "COPYING")
    check(os.path.isfile(lic), "upstream GPL-2 licence installed", lic)

    result = run([sys.executable, smem_bin, "--help"])
    check(result.returncode == 0, "smem --help exits 0",
          "rc=%d" % result.returncode)
    check("--source" in result.stdout and "--processfilter" in result.stdout,
          "smem --help documents the reporting options")
    return smem_bin, cap_bin


# ───────────────────── B. synthetic --source battery ────────────────────────

def test_synthetic(smem_bin, workdir):
    print("\n== B. reporting against a synthetic smemcap archive ==")
    archive = os.path.join(workdir, "synthetic.tar")
    cap_archive(archive)
    size = os.path.getsize(archive)
    check(size > 0, "synthetic capture archive written", "%d bytes" % size)

    # The fixture must be readable by an independent reader before it is used
    # to judge smem, otherwise a broken fixture would look like a broken tool.
    try:
        with tarfile.open(archive) as tf:
            members = {ti.name: ti for ti in tf.getmembers()}
            smaps_size = tf.getmember("1000/smaps").size
    except Exception as exc:  # noqa: BLE001 - surfaced as a failed check
        check(False, "synthetic archive is a valid tar", str(exc))
        return
    check(set(CAPTURE[i][0] for i in range(len(CAPTURE))) == set(members),
          "synthetic archive is a valid tar with the expected members",
          "%d members" % len(members))
    check(smaps_size == len(MAPS_1000),
          "smaps payload survives the smemcap header layout",
          "%d bytes" % smaps_size)

    # The command line deliberately contains a space, so the per-process table
    # is read right-to-left (see keyed_rows) and the full command string gets a
    # dedicated two-column check further down.
    cols = "pid name user maps swap uss pss rss vss"
    tail = cols.split()[3:]
    result = smem(smem_bin, archive, "-c", cols)
    check(result.returncode == 0, "per-process table exits 0",
          "rc=%d %s" % (result.returncode, result.stderr.strip()))
    lines = (result.stdout.splitlines() or [""])
    check(lines[0].split()[:3] == ["PID", "Name", "User"],
          "per-process table prints a header", lines[0])
    table = keyed_rows(result.stdout)
    for pid, want in EXPECTED.items():
        key = str(pid)
        if key not in table:
            check(False, "pid %s row present" % key, ", ".join(sorted(table)))
            continue
        cells = table[key]
        name, user = cells[1], cells[2]
        got = dict(zip(tail, cells[-len(tail):]))
        check(name == want["name"], "pid %s name" % key, "%r" % name)
        check(user == want["user"], "pid %s user" % key, "%r" % user)
        for field in ("maps", "swap", "uss", "pss", "rss", "vss"):
            check(got.get(field) == str(want[field]),
                  "pid %s %s" % (key, field), "%s" % got.get(field))

    # A two-column table leaves the command (which contains a space) intact as
    # the remainder of the row.
    result = smem(smem_bin, archive, "-c", "pid command")
    commands = {}
    for line in data_lines(result.stdout):
        pid, _, rest = line.strip().partition(" ")
        commands[pid] = rest.strip()
    for pid, want in EXPECTED.items():
        check(commands.get(str(pid)) == want["command"],
              "pid %s command" % pid, "%r" % commands.get(str(pid)))

    total_cols = "pid swap uss pss rss"
    result = smem(smem_bin, archive, "-c", total_cols, "-t")
    rules = [ln for ln in result.stdout.splitlines() if ln.startswith("---")]
    check(len(rules) == 1, "-t prints exactly one totals rule", str(len(rules)))
    line = totals_line(result.stdout)
    if line is None:
        check(False, "-t prints a totals row")
    else:
        cells = line.split()
        got = dict(zip(total_cols.split(), cells))
        check(got.get("pid") == str(len(EXPECTED)), "totals pid count",
              "%s" % got.get("pid"))
        for field in ("swap", "uss", "pss", "rss"):
            check(got.get(field) == str(TOTALS[field]),
                  "totals %s" % field, "%s" % got.get(field))

    result = smem(smem_bin, archive, "-c", "pid rss", "-k")
    check(result.returncode == 0, "-k (abbreviate) exits 0")
    check("23.0K" in result.stdout and "8.0K" in result.stdout,
          "-k renders kB suffixes with one decimal", result.stdout.strip())

    result = smem(smem_bin, archive, "-c", "pid uss pss rss", "-p", "-R", "34kB")
    check(result.returncode == 0, "-p with -R exits 0")
    for value in ("50.00%", "52.94%", "67.65%"):
        check(value in result.stdout, "-p renders %s of a 34kB -R budget" % value)

    # -P matches the process name and command line, not the pid, so "serve" selects
    # pid 1000 and leaves pid 1001 out.
    result = smem(smem_bin, archive, "-P", "serve", "-c", "pid pss")
    table = keyed_rows(result.stdout)
    check("1000" in table and "1001" not in table,
          "-P filters processes by name/command regex", ", ".join(sorted(table)))

    result = smem(smem_bin, archive, "-c", "pid pss", "-s", "uss", "-r")
    order = [k for k in keyed_rows(result.stdout) if k.isdigit()]
    check(order == ["1000", "1001"], "-s uss -r reverses the sort order", ", ".join(order))

    result = smem(smem_bin, archive, "-H")
    check(result.returncode == 0 and "PID" not in result.stdout,
          "-H suppresses the header row", ", ".join(result.stdout.splitlines()[:1]))

    map_cols = "map count pids avgpss pss rss swap uss"
    map_tail = map_cols.split()[1:]
    result = smem(smem_bin, archive, "-m", "-c", map_cols)
    check(result.returncode == 0, "-m (mappings) exits 0", result.stderr.strip())
    table = keyed_rows(result.stdout)
    for name, want in EXPECTED_MAPS.items():
        if name not in table:
            check(False, "mapping row %r present" % name, ", ".join(sorted(table)))
            continue
        cells = dict(zip(map_tail, table[name][-len(map_tail):]))
        for field in map_tail:
            check(cells.get(field) == str(want[field]),
                  "mapping %s %s" % (name, field), "%s" % cells.get(field))

    result = smem(smem_bin, archive, "-m", "-c", map_cols, "-M", "lib")
    table = keyed_rows(result.stdout)
    check("/lib/thing" in table and "[heap]" not in table,
          "-M filters mappings by regex", ", ".join(sorted(table)))

    user_cols = "user count swap uss pss rss"
    user_tail = user_cols.split()[1:]
    result = smem(smem_bin, archive, "-u")
    check(result.returncode == 0, "-u (users) exits 0", result.stderr.strip())
    table = keyed_rows(result.stdout)
    for user, want in EXPECTED_USERS.items():
        if user not in table:
            check(False, "user row %r present" % user, ", ".join(sorted(table)))
            continue
        cells = dict(zip(user_tail, table[user][-len(user_tail):]))
        for field in user_tail:
            check(cells.get(field) == str(want[field]),
                  "user %s %s" % (user, field), "%s" % cells.get(field))

    result = smem(smem_bin, archive, "-u", "-n")
    table = keyed_rows(result.stdout)
    check("1000" in table and "0" in table,
          "-u -n keeps owners numeric for capture archives", ", ".join(sorted(table)))

    # Area names contain spaces ("kernel dynamic memory"), so the three numeric
    # columns are taken off the right and everything left is the area name.
    result = smem(smem_bin, archive, "-w")
    check(result.returncode == 0, "-w (system) exits 0", result.stderr.strip())
    seen = {}
    for line in data_lines(result.stdout):
        cells = line.split()
        seen[" ".join(cells[:-3])] = tuple(cells[-3:])
    for area, want in EXPECTED_SYSTEM.items():
        if area not in seen:
            check(False, "system row %r present" % area, ", ".join(sorted(seen)))
            continue
        check(seen[area] == tuple(str(v) for v in want),
              "system %s used/cache/noncache" % area, "/".join(seen[area]))

    result = smem(smem_bin, archive, "-c", "nosuchcolumn")
    check(result.returncode != 0, "unknown column is rejected",
          "rc=%d" % result.returncode)
    check("unknown field" in result.stdout, "unknown column names the offender")

    result = smem(smem_bin, archive, "-s", "nosuchfield")
    check(result.returncode != 0 and "unknown field" in result.stdout,
          "unknown sort field is rejected", "rc=%d" % result.returncode)

    result = smem(smem_bin, archive, "-R", "123")
    check(result.returncode != 0 and "units" in result.stderr,
          "-R without a unit suffix is rejected", "rc=%d" % result.returncode)


# ───────────────────────── C. live capture on OHOS ─────────────────────────

def test_live_capture(smem_bin, cap_bin, workdir):
    print("\n== C. live /proc capture by the delivered smemcap ==")
    machine = platform.machine()
    if machine not in ("aarch64", "arm64"):
        print("SKIP delivered smemcap execution — build machine is %s, "
              "the OHOS AArch64 worker runs it natively" % machine)
        return
    archive = os.path.join(workdir, "live.tar")
    with open(archive, "wb") as sink:
        result = subprocess.run([cap_bin], stdout=sink, stderr=subprocess.PIPE)
    check(result.returncode == 0, "smemcap exits 0 on the live /proc",
          "rc=%d" % result.returncode)
    try:
        with tarfile.open(archive) as tf:
            names = [ti.name for ti in tf.getmembers()]
            meminfo = tf.extractfile("meminfo").read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - surfaced as a failed check
        check(False, "smemcap archive is a valid tar", str(exc))
        return
    check(len(names) > 3, "smemcap archived the live /proc tree",
          "%d members" % len(names))
    check("meminfo" in names, "smemcap archived /proc/meminfo")
    check(any(n.endswith("/smaps") for n in names),
          "smemcap archived per-pid smaps",
          "%d smaps entries" % sum(1 for n in names if n.endswith("/smaps")))
    check(bool(re.search(r"^MemTotal:\s+\d+ kB", meminfo, re.MULTILINE)),
          "captured meminfo parses with smem's own field regex")

    fields = dict(re.findall(r"^(\S+):\s+(\d+) kB", meminfo, re.MULTILINE))
    if "memtotal" not in fields or "swaptotal" not in fields:
        print("SKIP smem --source read-back — this kernel's /proc/meminfo has no "
              "MemTotal/SwapTotal pair (fields: %s)" % sorted(fields))
        return
    result = smem(smem_bin, archive, "-c", "pid pss")
    check(result.returncode == 0,
          "smem reads the archive smemcap just captured",
          "rc=%d %s" % (result.returncode, result.stderr.strip()))


def make_workdir():
    """Pick a scratch directory outside the source tree.

    The synthetic capture archive is a real file, so it must not be written
    anywhere under archives/ where a later `git add` would pick it up, and it
    must not assume a writable /tmp either.
    """
    for base in (os.environ.get("SMEM_TEST_WORKDIR"), tempfile.gettempdir(),
                 os.path.dirname(os.path.abspath(__file__))):
        if not base:
            continue
        try:
            return tempfile.mkdtemp(prefix="smem-consumer-", dir=base)
        except OSError:
            continue
    raise RuntimeError("no writable scratch directory available")


def main():
    if len(sys.argv) != 2:
        print("usage: test_smem.py <package-bin-dir>")
        return 2
    bindir = sys.argv[1]
    workdir = make_workdir()
    print("scratch directory: %s" % workdir)
    smem_bin, cap_bin = test_artifacts(bindir)
    test_synthetic(smem_bin, workdir)
    test_live_capture(smem_bin, cap_bin, workdir)
    print("\n%d checks passed, %d failed" % (PASSED, FAILED))
    if FAILED:
        print("SMEM CONSUMER TESTS FAILED")
        return 1
    print("ALL SMEM CONSUMER TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
