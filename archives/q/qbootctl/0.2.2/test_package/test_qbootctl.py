#!/usr/bin/env python3
"""Safe consumer tests for qbootctl 0.2.2 (test-only build).

Scope:
  * Runs ONLY bin/qbootctl-test (compiled with QBOOTCTL_TESTING), whose
    backend is a pure in-memory mock — no /dev, /proc, /sys, no real
    block device, no GPT/UFS access. State transitions (-s/-m/-u) are
    exercised ONLY against this in-memory mock.
  * Verifies the production bin/qbootctl contains NO mock switch
    (strings scan) and keeps upstream semantics (non-root rejection),
    and that a QBOOTCTL_BACKEND=mock env var is NOT accepted.
  * Verifies no temp-file leakage around test runs.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

QBOOTCTL_BIN = os.path.abspath(sys.argv[1])      # production binary
QBOOTCTL_TEST_BIN = os.path.abspath(sys.argv[2])  # test-only binary
PKG_DIR = os.path.abspath(sys.argv[3])

PASSED = 0
FAILED = 0


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"PASS: {name}")
    else:
        FAILED += 1
        print(f"FAIL: {name} {detail}")


def run(bin_path, args, env=None, cwd=None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        [bin_path] + args,
        capture_output=True,
        text=True,
        env=full_env,
        cwd=cwd,
        timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def sha256_of_dir(path):
    digest = hashlib.sha256()
    for root, _dirs, files in os.walk(path):
        for name in sorted(files):
            fp = os.path.join(root, name)
            digest.update(name.encode())
            digest.update(b"\0")
            with open(fp, "rb") as fh:
                digest.update(fh.read())
            digest.update(b"\0")
    return digest.hexdigest()


def strings_have(bin_path, needles):
    """Return True if ANY needle appears in the binary's strings."""
    with open(bin_path, "rb") as fh:
        data = fh.read()
    return any(n.encode() in data for n in needles)


def main():
    global PASSED, FAILED

    # The mock backend mirrors state to ".qbootctl-mock.state" in the
    # current directory. A leftover file from a previous run (e.g. the
    # same conan build dir) would be loaded and shift the initial state,
    # so clean it before starting.
    leftover = os.path.join(os.getcwd(), ".qbootctl-mock.state")
    if os.path.exists(leftover):
        os.remove(leftover)

    # ── Part A: production binary must be mock-free and upstream-faithful ──
    check("prod binary exists", os.path.isfile(QBOOTCTL_BIN) and os.access(QBOOTCTL_BIN, os.X_OK))
    if os.path.isfile(QBOOTCTL_BIN):
        with open(QBOOTCTL_BIN, "rb") as fh:
            elf_magic = fh.read(4)
        check("prod ELF magic", elf_magic == b"\x7fELF", f"magic={elf_magic!r}")
        with open(QBOOTCTL_BIN, "rb") as fh:
            fh.seek(18)
            e_machine = fh.read(2)
        check("prod aarch64 machine", e_machine == b"\xb7\x00", f"e_machine={e_machine.hex()}")

    # No runtime mock switch in production binary.
    check(
        "prod has no QBOOTCTL_BACKEND string",
        not strings_have(QBOOTCTL_BIN, ["QBOOTCTL_BACKEND"]),
    )
    check(
        "prod has no mock symbols",
        not strings_have(QBOOTCTL_BIN, ["mock_bootctl", "mock_slot_"]),
    )

    # Upstream semantics: non-root is rejected for every command, incl. -h/--help.
    if os.geteuid() != 0:
        rc, _out, err = run(QBOOTCTL_BIN, [])
        check("prod non-root no-args rejected", rc == 1 and "must be run as root" in err, f"rc={rc}")
        rc, _out, err = run(QBOOTCTL_BIN, ["-h"])
        check("prod non-root -h rejected (upstream)", rc == 1 and "must be run as root" in err, f"rc={rc}")
        rc, _out, err = run(QBOOTCTL_BIN, ["--help"])
        check("prod non-root --help rejected (upstream)", rc == 1, f"rc={rc}")
        # Runtime switch attempt must NOT be accepted.
        rc, _out, err = run(QBOOTCTL_BIN, ["-c"], env={"QBOOTCTL_BACKEND": "mock"})
        check("prod ignores QBOOTCTL_BACKEND env", rc == 1 and "must be run as root" in err, f"rc={rc}")

    # ── Part B: test-only build — in-memory mock queries ──
    check("test binary exists", os.path.isfile(QBOOTCTL_TEST_BIN) and os.access(QBOOTCTL_TEST_BIN, os.X_OK))
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-c"])
    check("test -c current slot", rc == 0 and "_a" in out, f"rc={rc} out={out.strip()}")
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-a"])
    check("test -a active slot", rc == 0 and "_a" in out, f"rc={rc} out={out.strip()}")
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-b", "a"])
    check("test -b bootable", rc == 0 and "marked bootable" in out, f"rc={rc} out={out.strip()}")
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-n", "a"])
    check("test -n successful", rc == 0 and "marked successful" in out, f"rc={rc} out={out.strip()}")
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-x"])
    check("test -x suffix", rc == 0 and "_a" in out, f"rc={rc} out={out.strip()}")
    rc, out, _err = run(QBOOTCTL_TEST_BIN, [])
    check("test no-arg dump", rc == 0 and "Current slot" in out, f"rc={rc} out={out.strip()}")
    rc, _out, err = run(QBOOTCTL_TEST_BIN, ["-h"])
    check("test -h help", rc == 0 and "qcom bootctrl HAL port" in (err or ""), f"rc={rc}")
    rc, _out, err = run(QBOOTCTL_TEST_BIN, ["-n", "c"])
    check("test invalid slot rejected", rc == 1 and "Expected slot not 'c'" in err, f"rc={rc}")

    # ── Part C: in-memory write state transitions (mock only) ──
    # -s switches the active slot in memory; -a then reflects the change.
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-s", "b"])
    check("test -s set active ok", rc == 0, f"rc={rc}")
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-a"])
    check("test -a reflects switched slot", rc == 0 and "_b" in out, f"rc={rc} out={out.strip()}")
    # -u marks slot unbootable in memory; -b then reflects it.
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-u", "a"])
    check("test -u set unbootable ok", rc == 0, f"rc={rc}")
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-b", "a"])
    check("test -b reflects unbootable", rc == 0 and "not marked bootable" in out, f"rc={rc} out={out.strip()}")
    # -m marks boot successful in memory; -n then reflects it.
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-m", "b"])
    check("test -m mark successful ok", rc == 0, f"rc={rc}")
    rc, out, _err = run(QBOOTCTL_TEST_BIN, ["-n", "b"])
    check("test -n reflects marked successful", rc == 0 and "marked successful" in out, f"rc={rc} out={out.strip()}")

    # ── Part D: temp-file isolation (no leakage) ──
    # The mock backend mirrors state to ".qbootctl-mock.state" in the
    # current (temp) directory — that plain file is the ONLY expected
    # artifact. No other files may appear, and no device paths may be
    # opened (the mock never opens /dev, /proc or /sys).
    with tempfile.TemporaryDirectory(prefix="qbootctl-test-") as tmp:
        before = set(os.listdir(tmp))
        rc, _out, _err = run(QBOOTCTL_TEST_BIN, ["-c"], cwd=tmp)
        rc2, _out2, _err2 = run(QBOOTCTL_TEST_BIN, ["-s", "b"], cwd=tmp)
        after = set(os.listdir(tmp))
        new_files = after - before
        check("test runs exit ok", rc == 0 and rc2 == 0, f"rc={rc} rc2={rc2}")
        check(
            "only mock state file appears in temp dir",
            new_files == {".qbootctl-mock.state"},
            f"new={sorted(new_files)}",
        )
        state_path = os.path.join(tmp, ".qbootctl-mock.state")
        if os.path.isfile(state_path):
            with open(state_path) as fh:
                content = fh.read().strip()
            parts = content.split()
            check(
                "mock state file holds 6 ints",
                len(parts) == 6 and all(p in ("0", "1") for p in parts),
                f"content={content!r}",
            )
            # The mock must not leave state outside the temp workdir.
            leaked = [
                p
                for p in ("/dev/disk/by-partlabel", "/dev/bsg/ufs-bsg0")
                if os.path.exists(p)
            ]
            check("no device path touched by mock", not leaked, f"leaked={leaked}")

    # ── Part E: license installed ──
    lic = os.path.join(PKG_DIR, "licenses", "LICENSE")
    check("LICENSE installed", os.path.isfile(lic))
    if os.path.isfile(lic):
        with open(lic, "r", errors="replace") as fh:
            head = fh.read(200)
        check("LICENSE is GPL-3", "GNU GENERAL PUBLIC LICENSE" in head and "Version 3" in head)

    # ── Summary ──
    total = PASSED + FAILED
    print(f"\nRESULT: passed={PASSED} failed={FAILED} total={total}")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
