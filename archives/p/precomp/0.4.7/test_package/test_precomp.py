#!/usr/bin/env python3
"""Verify the packaged precomp binary (R34 — executes the package's binary).

Assertion targets were derived from the observed behaviour of the tool
(README + manual runs), not guessed:

1. --version    -> rc=0 and the version banner on stdout
2. --help       -> rc=0 and the "Usage: precomp [-switches]" text
3. precompress  -> weak deflate (gzip level 1) input yields a .pcf, rc=0,
                   "Recompressed streams: 1/1"
4. restore      -> `precomp -r` on the .pcf reproduces the original file
                   byte-for-byte (sha256 round-trip)
5. value proof  -> gzip(pcf) is strictly smaller than gzip(original .gz)
                   (precomp's core value proposition: a stronger compressor
                   does better on the uncompressed .pcf payload)

All work happens inside tempfile.mkdtemp() and is cleaned up in finally.
Every subprocess call carries a timeout.
"""
import gzip
import hashlib
import os
import random
import shutil
import subprocess
import sys
import tempfile

failures = []


def check(label, cond, detail=""):
    if cond:
        print(f"  [OK] {label}")
    else:
        failures.append(label)
        print(f"  [FAIL] {label} {detail}")


def run(binary, args, timeout=180):
    """Run precomp with args; return the CompletedProcess."""
    return subprocess.run([binary] + args, capture_output=True,
                          text=True, timeout=timeout)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    binary = os.path.abspath(sys.argv[1])
    workdir = tempfile.mkdtemp(prefix="precomp-test-")
    try:
        # 1. --version exits 0 with the version banner
        r = run(binary, ["--version"])
        check("--version rc=0 with version banner",
              r.returncode == 0 and "Precomp v0.4.7" in (r.stdout + r.stderr),
              f"rc={r.returncode}")

        # 2. --help exits 0 with usage text
        r = run(binary, ["--help"])
        check("--help rc=0 with usage text",
              r.returncode == 0 and "Usage: precomp" in (r.stdout + r.stderr),
              f"rc={r.returncode}")

        # Build the test input: ~115 KiB of wordy text wrapped in a weak
        # (level 1) deflate container — the classic precomp use case.
        random.seed(20260904)
        words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy",
                 "dog", "precomp", "harmony", "ohos", "aarch64"]
        content = (" ".join(random.choice(words)
                            for _ in range(20000))).encode()
        src = os.path.join(workdir, "sample.txt.gz")
        with gzip.open(src, "wb", compresslevel=1) as f:
            f.write(content)
        src_hash = sha256_file(src)

        # 3. precompress into a .pcf
        pcf = os.path.join(workdir, "sample.txt.pcf")
        r = run(binary, [f"-o{pcf}", src])
        check("precompress rc=0, .pcf created, 1/1 stream recompressed",
              r.returncode == 0 and os.path.isfile(pcf)
              and os.path.getsize(pcf) > 0
              and "Recompressed streams: 1/1" in (r.stdout + r.stderr),
              f"rc={r.returncode}")

        # 4. restore round-trip is byte-identical
        restored = os.path.join(workdir, "restored.txt.gz")
        r = run(binary, ["-r", f"-o{restored}", pcf])
        check("restore round-trip byte-identical (sha256 match)",
              r.returncode == 0 and os.path.isfile(restored)
              and sha256_file(restored) == src_hash,
              f"rc={r.returncode}")

        # 5. a stronger compressor does better on the .pcf payload
        with open(src, "rb") as f:
            orig_bytes = f.read()
        with open(pcf, "rb") as f:
            pcf_bytes = f.read()
        c_orig = len(gzip.compress(orig_bytes, 9))
        c_pcf = len(gzip.compress(pcf_bytes, 9))
        check(f"gzip(.pcf) < gzip(original): {c_pcf} < {c_orig}",
              c_pcf < c_orig)

        passed = 5 - len(failures)
        print(f"HMBS_TEST_PACKAGE_RESULT: total=5 passed={passed} "
              f"failed={len(failures)}")
        return 1 if failures else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
