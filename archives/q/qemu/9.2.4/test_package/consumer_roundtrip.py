#!/usr/bin/env python3
"""End-to-end consumer case for the qemu package on HarmonyOS PC (rule12).

This is *one* complete consumer case, not a bag of assertions: it drives the
packaged engine through a full storage workflow and then proves the result
against a reference file that was built independently of QEMU.

    construct input  -> 16 MiB reference built from python bytes (deterministic,
                        no random data), laid out as two fixed patterns
    real execution   -> the packaged qemu-img / qemu-io create a qcow2 image,
                        write both patterns, verify the image, then convert it
                        to raw, to a compressed qcow2 and to vmdk
    deterministic out-> the converted payloads are written to disk
    verify content   -> every payload is compared byte for byte with the
                        reference, a second conversion is compared with the
                        first (determinism), and a negative control proves the
                        pattern check really fires on mismatched data

Using QEMU's own output as the golden file would be self-certifying, so the
reference here comes from python's own bytes concatenation instead.

Usage: consumer_roundtrip.py <package bin dir> <work dir>
Exit code 0 only when every check passes.
"""
import os
import subprocess
import sys

REGION = 64 * 1024
OFF1 = 0
OFF2 = 1024 * 1024
SIZE = 16 * 1024 * 1024
PAT1 = 0x5A
PAT2 = 0xA5
CHUNK = 1 << 20


def run(cmd, timeout=600):
    done = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=timeout)
    return done.returncode, done.stdout.decode("utf-8", "replace")


def first_difference(path_a, path_b):
    """Return None when the two files are byte identical, else a description."""
    size_a, size_b = os.path.getsize(path_a), os.path.getsize(path_b)
    if size_a != size_b:
        return "size %d != %d" % (size_a, size_b)
    offset = 0
    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        while True:
            block_a, block_b = fa.read(CHUNK), fb.read(CHUNK)
            if block_a != block_b:
                limit = min(len(block_a), len(block_b))
                for i in range(limit):
                    if block_a[i] != block_b[i]:
                        return "byte %d differs" % (offset + i)
                return "length differs at offset %d" % (offset + limit)
            if not block_a:
                return None
            offset += len(block_a)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    bin_dir, work = sys.argv[1], sys.argv[2]
    qemu_img = os.path.join(bin_dir, "qemu-img")
    qemu_io = os.path.join(bin_dir, "qemu-io")
    for tool in (qemu_img, qemu_io):
        if not os.path.isfile(tool):
            print("missing packaged tool: %s" % tool)
            return 2
    os.makedirs(work, exist_ok=True)

    image = os.path.join(work, "consumer.qcow2")
    reference = os.path.join(work, "reference.bin")
    raw_first = os.path.join(work, "consumer.raw")
    raw_again = os.path.join(work, "consumer-again.raw")
    compressed = os.path.join(work, "consumer-compressed.qcow2")
    raw_compressed = os.path.join(work, "consumer-compressed.raw")
    vmdk = os.path.join(work, "consumer.vmdk")
    raw_vmdk = os.path.join(work, "consumer-vmdk.raw")

    checks = []

    def check(label, ok, detail=""):
        checks.append((label, bool(ok)))
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                               (" -- " + str(detail).replace("\n", " ")[:80]) if detail else ""))

    print("== phase 1: construct the input")
    payload = bytearray(SIZE)
    payload[OFF1:OFF1 + REGION] = bytes([PAT1]) * REGION
    payload[OFF2:OFF2 + REGION] = bytes([PAT2]) * REGION
    with open(reference, "wb") as handle:
        handle.write(bytes(payload))

    print("== phase 2: run the packaged engine")
    rc, out = run([qemu_img, "create", "-f", "qcow2", image, "16M"])
    check("qemu-img create builds the 16 MiB qcow2 image",
          rc == 0 and os.path.isfile(image), out.strip()[-70:])

    rc, out = run([qemu_io, "-f", "qcow2",
                   "-c", "write -P 0x5a 0 64k",
                   "-c", "write -P 0xa5 1048576 64k", image])
    check("qemu-io writes both fixed patterns into the image", rc == 0, out.strip()[-70:])

    rc, out = run([qemu_img, "check", image])
    check("qemu-img check reports no errors",
          rc == 0 and "No errors were found" in out, out.strip()[:80])

    print("== phase 3: deterministic artefacts")
    rc, out = run([qemu_img, "convert", "-f", "qcow2", "-O", "raw", image, raw_first])
    check("qemu-img convert produces a raw image", rc == 0 and os.path.isfile(raw_first),
          out.strip()[-70:])

    rc, out = run([qemu_img, "convert", "-f", "qcow2", "-O", "raw", image, raw_again])
    diff = first_difference(raw_first, raw_again) if rc == 0 else "convert failed"
    check("a second conversion is byte identical (deterministic)", rc == 0 and diff is None, diff)

    rc, out = run([qemu_img, "convert", "-c", "-f", "qcow2", "-O", "qcow2", image, compressed])
    check("qemu-img convert -c writes a compressed qcow2 image",
          rc == 0 and os.path.isfile(compressed), out.strip()[-70:])

    rc, out = run([qemu_img, "convert", "-f", "qcow2", "-O", "raw", compressed, raw_compressed])
    diff = first_difference(raw_first, raw_compressed) if rc == 0 else "convert failed"
    check("the compressed image reads back to the same payload", rc == 0 and diff is None, diff)

    rc, out = run([qemu_img, "convert", "-f", "qcow2", "-O", "vmdk", image, vmdk])
    check("qemu-img convert writes a vmdk image", rc == 0 and os.path.isfile(vmdk),
          out.strip()[-70:])

    rc, out = run([qemu_img, "convert", "-f", "vmdk", "-O", "raw", vmdk, raw_vmdk])
    diff = first_difference(raw_first, raw_vmdk) if rc == 0 else "convert failed"
    check("the vmdk round trip preserves the payload", rc == 0 and diff is None, diff)

    print("== phase 4: verify the content")
    diff = first_difference(raw_first, reference)
    check("the raw payload matches the independent reference byte for byte",
          diff is None, diff)

    rc, out = run([qemu_io, "-f", "qcow2", "-c", "read -P 0x5a 0 64k", image])
    check("qemu-io verifies the first pattern inside the image",
          rc == 0 and "read 65536/65536" in out, out.strip()[:60])

    rc, out = run([qemu_io, "-f", "qcow2", "-c", "read -P 0xa5 0 64k", image])
    check("negative control: a mismatching pattern is reported",
          "Pattern verification failed" in out, out.strip()[:60])

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    print("consumer round trip: %d/%d checks passed" % (passed, total))
    failed = [label for label, ok in checks if not ok]
    if failed:
        print("FAILED: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
