#!/usr/bin/env python3
"""Reproducibility probe for the bambamc Conan package (L5 supplement).

Two clean-cache `conan create` runs produce byte-identical archives for 39 of
the 40 packaged files; only `lib/libbambamc.a` differs.  This script shows
*why* and provides a metric that is actually stable across rounds.

Usage:
    python3 repro-check.py <libbambamc-A.a> <libbambamc-B.a> <builddir-A> <builddir-B>

The build directories are the per-round Conan cache build folders
(`.../p/b/bamba<hash>/b`), which is where the varying path string comes from.

What it does
------------
1. Extracts every `ar` member of both archives.
2. Reports which members differ byte-for-byte and in which ELF section the
   differing bytes live  -> expected: `.rodata.str1.1`, because the build
   compiles with assertions enabled and `assert()` embeds `__FILE__`, i.e. the
   absolute source path containing the per-round cache build directory hash.
3. Rewrites name, then rebuilds the whole archive.
4. Normalises the per-round build directory hash out of every member and
   diffs again -> expected: no differences, i.e. the archive content is
   reproducible modulo the build directory name.

Exit code 0 only if step 4 found no differences.
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile


def extract(archive, dest):
    os.makedirs(dest, exist_ok=True)
    subprocess.run(["ar", "x", archive], cwd=dest, check=True)
    return sorted(f for f in os.listdir(dest) if f.endswith(".o"))


def sections_of(obj):
    """name -> (file offset, size) for every section, via llvm-readelf."""
    out = subprocess.run(["llvm-readelf", "-S", obj], capture_output=True, text=True).stdout
    sections = []
    for line in out.splitlines():
        m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)", line)
        if m:
            name, _type, _addr, off, size = m.groups()
            sections.append((name, int(off, 16), int(size, 16)))
    return sections


def locate(sections, offset):
    for name, off, size in sections:
        if off <= offset < off + size:
            return name
    return "<none>"


def normalise(data, hash_pattern):
    return re.sub(hash_pattern, b"BAMBAHASH", data)


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    arch_a, arch_b, dir_a, dir_b = sys.argv[1:5]
    # The varying token is the per-round cache build folder name, e.g. `bamba3f2a...`.
    # Do NOT use basename(dir) for the guard below: callers naturally pass
    # `.../bamba<hash>/b`, whose basename is just "b" for both rounds.
    hash_pattern = re.compile(rb"bamba[0-9a-f]{12,}")
    build_a = hash_pattern.search(dir_a.encode()).group(0) if hash_pattern.search(dir_a.encode()) else b""
    build_b = hash_pattern.search(dir_b.encode()).group(0) if hash_pattern.search(dir_b.encode()) else b""

    tmp = tempfile.mkdtemp(prefix="repro-")
    a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
    members_a = extract(arch_a, a)
    members_b = extract(arch_b, b)

    print("members: A=%d B=%d  identical name lists=%s"
          % (len(members_a), len(members_b), members_a == members_b))
    if members_a != members_b:
        print("FAIL: ar member lists differ")
        return 1

    if not build_a or not build_b:
        print("note: no 'bamba<hex>' token found in the supplied build dirs; "
              "path echo below is limited to whatever the objects contain")

    differing = []
    section_hits = {}
    for name in members_a:
        da = open(os.path.join(a, name), "rb").read()
        db = open(os.path.join(b, name), "rb").read()
        if da == db:
            continue
        differing.append(name)
        offs = [i for i in range(min(len(da), len(db))) if da[i] != db[i]]
        secs = sections_of(os.path.join(a, name))
        for off in offs:
            section_hits[locate(secs, off)] = section_hits.get(locate(secs, off), 0) + 1
        print("  differs: %-55s bytes=%-3d sections=%s"
              % (name, len(offs), sorted({locate(secs, o) for o in offs})))
        for label, data, want in (("A", da, build_a), ("B", db, build_b)):
            found = re.search(rb"[\x20-\x7e]*bamba[0-9a-f]{12,}[\x20-\x7e]*", data)
            if found and (not want or want in data):
                print("      %s path=%s" % (label, found.group(0).decode("ascii", "replace")))

    print("differing members: %d/%d   sections touched: %s"
          % (len(differing), len(members_a), section_hits))

    still = []
    for name in members_a:
        da = normalise(open(os.path.join(a, name), "rb").read(), hash_pattern)
        db = normalise(open(os.path.join(b, name), "rb").read(), hash_pattern)
        if da != db:
            still.append(name)

    digest = hashlib.sha256()
    for name in members_a:
        digest.update(name.encode())
        digest.update(normalise(open(os.path.join(a, name), "rb").read(), hash_pattern))
    print("normalised content fingerprint (A) = %s" % digest.hexdigest())

    if still:
        print("FAIL: %d members still differ after normalising the build dir hash: %s"
              % (len(still), still[:5]))
        return 1
    print("PASS: all %d members byte-identical after normalising the build directory hash"
          % len(members_a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
