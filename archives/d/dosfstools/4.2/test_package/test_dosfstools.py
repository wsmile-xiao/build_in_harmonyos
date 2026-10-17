#!/usr/bin/env python3
"""Consumer assertions for dosfstools 4.2 on HarmonyOS PC.

The tools are exercised on a regular file image (S_ISREG path), which is the
upstream-supported, unprivileged surface on this platform:

  1. mkfs.fat -F 16 -n TESTVOL formats a 16 MiB file image
  2. the FAT boot sector carries the expected jump signature
  3. the volume label lands in the BPB volume-label field (offset 43)
  4. fsck.fat -a accepts the freshly formatted image (rc == 0)
  5. the installed mkfs.vfat / fsck.vfat aliases exist (install-exec-hook)
  6. the fsck.vfat alias runs on the image (rc == 0)
  7. fatlabel rewrites the label and reads it back verbatim
  8. negative control: fsck.fat -n on a zero-filled file must fail

The block-device/mount face (loop devices, losetup, mount) is unavailable to
unprivileged users on this platform; it is a different face of the tool, not
this deliverable's asserted surface, so it is intentionally not tested here.
"""

import os
import subprocess
import sys
import tempfile

CHECKS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"{status}: {name}" + (f" ({detail})" if detail else ""))
    CHECKS.append((name, bool(cond)))


def run(args):
    proc = subprocess.run(
        args, capture_output=True, text=True, timeout=180, check=False
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _workdir():
    """Scratch dir OUTSIDE the recipe tree (device /tmp is read-only; writing
    next to test_package would drop image artifacts into the repository)."""
    bases = [b for b in (os.environ.get("TMPDIR"),
                         os.path.join(os.path.expanduser("~"), "tmp")) if b]
    bases.append(os.getcwd())
    for base in bases:
        try:
            os.makedirs(base, exist_ok=True)
            if os.access(base, os.W_OK):
                return tempfile.mkdtemp(prefix="dosfstools-consumer-", dir=base)
        except OSError:
            continue
    raise SystemExit("no writable scratch directory for the consumer test")


def main(bindir):
    workdir = _workdir()
    img = os.path.join(workdir, "consumer.img")
    with open(img, "wb") as handle:
        handle.truncate(16 * 1024 * 1024)

    mkfs = os.path.join(bindir, "mkfs.fat")
    fsck = os.path.join(bindir, "fsck.fat")
    label = os.path.join(bindir, "fatlabel")
    fsck_vfat = os.path.join(bindir, "fsck.vfat")
    mkfs_vfat = os.path.join(bindir, "mkfs.vfat")

    rc, _ = run([mkfs, "-F", "16", "-n", "TESTVOL", img])
    check("mkfs.fat formats a regular file image", rc == 0, f"rc={rc}")

    with open(img, "rb") as handle:
        boot = handle.read(512)
    check(
        "FAT boot sector jump signature (eb xx 90)",
        len(boot) == 512 and boot[0] == 0xEB and boot[2] == 0x90,
        boot[:3].hex(),
    )
    check(
        "volume label TESTVOL in BPB label field",
        b"TESTVOL" in boot[43:54],
        boot[43:54].decode("ascii", "replace"),
    )

    rc, out = run([fsck, "-a", img])
    check("fsck.fat -a accepts freshly formatted image", rc == 0, f"rc={rc}")

    check("mkfs.vfat alias installed", os.path.exists(mkfs_vfat), mkfs_vfat)
    check("fsck.vfat alias installed", os.path.exists(fsck_vfat), fsck_vfat)
    if os.path.exists(fsck_vfat):
        rc, _ = run([fsck_vfat, img])
        check("fsck.vfat alias runs on image", rc == 0, f"rc={rc}")
    else:
        check("fsck.vfat alias runs on image", False, "alias missing")

    rc, _ = run([label, img, "TESTLAB"])
    check("fatlabel rewrites the volume label", rc == 0, f"rc={rc}")

    rc, out = run([label, img])
    check(
        "fatlabel reads back TESTLAB",
        rc == 0 and out.splitlines()[-1].strip() == "TESTLAB",
        f"rc={rc} out={out.splitlines()[-1].strip() if out else ''!r}",
    )

    blank = os.path.join(workdir, "not-a-fat.img")
    with open(blank, "wb") as handle:
        handle.truncate(1024 * 1024)
    rc, out = run([fsck, "-n", blank])
    check("negative control: fsck.fat rejects a zero-filled file", rc != 0, f"rc={rc}")

    passed = sum(1 for _, ok in CHECKS if ok)
    total = len(CHECKS)
    print(f"CONSUMER ASSERTIONS: {passed}/{total} passed")
    if passed != total:
        print("FAILED:", [name for name, ok in CHECKS if not ok])
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_dosfstools.py <bindir>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
