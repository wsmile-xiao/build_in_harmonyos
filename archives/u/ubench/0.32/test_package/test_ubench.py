#!/usr/bin/env python3
"""Consumer tests for the packaged bin/ubench (ubench 0.32).

Cases (the full 3+3 minute benchmark is not run here; -s "single" mode
calibrates the same workloads to a 0.4 s reference and reports at once):

  1. bad option          -> exit 1, version banner + "Usage: ubench [-cmhs]"
  2. -cs  single CPU     -> exit 0, uname line, "Ubench Single CPU: N (T s)", N > 0
  3. -ms  single MEM     -> exit 0, "Ubench Single MEM: N (T s)", N > 0
  4. -cms both           -> exit 0, "Ubench Single AVG" == (CPU + MEM) / 2
  5. [HarmonyOS] artefact: ELF64 AArch64, OHOS NDK note (".note.ohos.ident",
     owner "OHOS"), static PIE (ET_DYN, no PT_INTERP) — runs without
     /lib/ld-musl-aarch64.so.1
  6. [HarmonyOS] CLK_TCK patch on OHOS libc: the seconds printed in cases 2-3
     come from times() / sysconf(_SC_CLK_TCK); the calibration targets 0.4 s,
     so 0.1 <= T <= 2.0 proves the tick rate is taken from the OHOS libc (a
     wrong constant such as CLOCKS_PER_SEC would be off by >= 10x or 10^4x),
     and the uname line must report machine "aarch64"
  7. [HarmonyOS] sys_errlist patch on OHOS musl: with RLIMIT_NOFILE=4 both
     pipe() calls fail with EMFILE and ubench must print OHOS musl's own
     strerror text "No file descriptors available" (glibc's text would be
     "Too many open files"), then exit 0 without scores

The binary runs natively on AArch64 (the HarmonyOS CI device) and through
qemu-aarch64 elsewhere; neither available is a failure, never a skip.
"""
import argparse
import platform
import re
import resource
import shutil
import struct
import subprocess
import sys

EM_AARCH64 = 183
ET_DYN = 3
PT_INTERP = 3
PT_NOTE = 4
BANNER = "Unix Benchmark Utility v.0.3"
checks = 0


def fail(msg):
    sys.exit("ubench test FAILED: " + msg)


def ok(msg):
    global checks
    checks += 1
    print("ok   " + msg, flush=True)


def elf_facts(path):
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        fail("not an ELF64 little-endian file")
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    e_phoff = struct.unpack_from("<Q", data, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)
    interp, owners = None, set()
    for i in range(e_phnum):
        p_type, _, p_offset, _, _, p_filesz = struct.unpack_from(
            "<IIQQQQ", data, e_phoff + i * e_phentsize)
        seg = data[p_offset:p_offset + p_filesz]
        if p_type == PT_INTERP:
            interp = seg.rstrip(b"\0").decode()
        elif p_type == PT_NOTE:
            pos = 0
            while pos + 12 <= len(seg):
                namesz, descsz, _ = struct.unpack_from("<III", seg, pos)
                owners.add(seg[pos + 12:pos + 12 + namesz].rstrip(b"\0").decode("latin-1"))
                pos += 12 + ((namesz + 3) & ~3) + ((descsz + 3) & ~3)
    return e_type, e_machine, interp, owners


def run(cmd, nofile=None):
    def limit():
        resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, nofile))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                          preexec_fn=limit if nofile else None)
    return proc.returncode, proc.stdout, proc.stderr


def score(out, kind):
    m = re.search(r"^Ubench Single %s: +(\d+) \((\d+\.\d\d)s\)$" % kind, out, re.M)
    if not m:
        fail("no 'Ubench Single %s' line in %r" % (kind, out))
    return int(m.group(1)), float(m.group(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", required=True)
    ap.add_argument("--ohos", action="store_true", help="target os is OHOS")
    args = ap.parse_args()

    if args.ohos:
        e_type, e_machine, interp, owners = elf_facts(args.binary)
        if e_machine != EM_AARCH64:
            fail("e_machine %d, expected AArch64 (183)" % e_machine)
        if "OHOS" not in owners:
            fail("no OHOS NDK note, owners %s" % sorted(owners))
        if e_type != ET_DYN or interp is not None:
            fail("expected static PIE, got e_type=%d interp=%r" % (e_type, interp))
        ok("[HarmonyOS] artefact: ELF64 AArch64, OHOS note, static PIE (no PT_INTERP)")

    if platform.machine().lower() in ("aarch64", "arm64"):
        runner = []
    else:
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            fail("non-AArch64 runner (%s) and no qemu-aarch64" % platform.machine())
        runner = [qemu]
    print("runner: %s" % (runner[0] if runner else "native"), flush=True)
    ubench = runner + [args.binary]

    rc, out, err = run(ubench + ["-x"])
    if rc != 1 or BANNER not in out or "Usage: ubench [-cmhs]" not in err:
        fail("bad option: rc=%d out=%r err=%r" % (rc, out, err))
    ok("bad option -> exit 1 with banner and usage")

    results = {}
    for flag, kind in (("-cs", "CPU"), ("-ms", "MEM")):
        rc, out, err = run(ubench + [flag])
        if rc != 0 or BANNER not in out:
            fail("%s: rc=%d out=%r err=%r" % (flag, rc, out, err))
        uname = out.splitlines()[4].split()
        if args.ohos and uname[-1] != "aarch64":
            fail("%s: uname machine %r, expected aarch64" % (flag, uname[-1]))
        value, secs = score(out, kind)
        if value <= 0:
            fail("%s: score %d" % (flag, value))
        if not 0.1 <= secs <= 2.0:
            fail("%s: calibrated run took %.2fs by times()/sysconf(_SC_CLK_TCK), "
                 "expected ~0.4s" % (flag, secs))
        results[kind] = value
        ok("%s -> Ubench Single %s %d, %.2fs via sysconf(_SC_CLK_TCK), uname %s"
           % (flag, kind, value, secs, uname[-1]))
    if args.ohos:
        ok("[HarmonyOS] CLK_TCK -> sysconf(_SC_CLK_TCK) timing within 0.1-2.0s on aarch64")

    rc, out, err = run(ubench + ["-cms"])
    if rc != 0:
        fail("-cms: rc=%d err=%r" % (rc, err))
    cpu, _ = score(out, "CPU")
    mem, _ = score(out, "MEM")
    m = re.search(r"^Ubench Single AVG: +(\d+)$", out, re.M)
    if not m or int(m.group(1)) != (cpu + mem) // 2:
        fail("-cms: AVG line wrong in %r" % out)
    ok("-cms -> AVG %s == (%d + %d) / 2" % (m.group(1), cpu, mem))

    rc, out, err = run(ubench + ["-cms"], nofile=4)
    want = ["****  cpubench: pipe: No file descriptors available",
            "****  membench: pipe: No file descriptors available"]
    if rc != 0 or any(w not in err for w in want) or "Ubench Single" in out:
        fail("EMFILE path: rc=%d out=%r err=%r" % (rc, out, err))
    ok("%sRLIMIT_NOFILE=4 -> strerror(EMFILE) from musl: 'No file descriptors available'"
       % ("[HarmonyOS] " if args.ohos else ""))

    print("all %d ubench checks passed" % checks, flush=True)


if __name__ == "__main__":
    main()
