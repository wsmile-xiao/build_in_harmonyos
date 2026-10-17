#!/usr/bin/env python3
"""Functional test harness for the installed tinyxxd binary.

Usage: test_tinyxxd.py <path-to-tinyxxd> <result-json> [workdir]

It reproduces the self-contained upstream cases — testfiles/test13.sh,
testfiles/test14.sh, testfiles/test15.sh, testfiles/test_c0.sh and the
xxd-independent cases of `make test` (help/error streams, little-endian
padding, CRLF revert, dump+revert round-trip) — and adds two consumer checks.
Writes a machine readable summary for the Conan test_package to consume.
"""
import json
import os
import subprocess
import sys
import tempfile


def main():
    exe = sys.argv[1]
    result_path = sys.argv[2]
    workdir = sys.argv[3] if len(sys.argv) > 3 else tempfile.mkdtemp(
        prefix="tinyxxd-", dir=os.environ.get("TMPDIR") or os.path.expanduser("~"))
    os.makedirs(workdir, exist_ok=True)

    upstream = []
    consumer = []

    def record(bucket, name, ok, detail=""):
        bucket.append((name, bool(ok)))
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}" + (f"  -- {detail}" if detail and not ok else ""))

    def run(args, stdin=None):
        proc = subprocess.run([exe] + args, input=stdin,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=workdir)
        return proc.returncode, proc.stdout, proc.stderr

    def write_file(name, data):
        path = os.path.join(workdir, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    # ── upstream: make test help / error stream cases ────────────────────
    rc, out, err = run(["-h"])
    record(upstream, "make test: -h writes usage to stdout", rc == 0 and b"Usage" in out)
    rc, out, err = run(["-Z"])
    record(upstream, "make test: bad option writes usage to stderr", rc != 0 and b"Usage" in err)

    # ── upstream: testfiles/test13.sh (-i -b) ────────────────────────────
    write_file("XXDfile", b"TESTabcd09\n")
    rc, out, err = run(["-i", "-b", "XXDfile"])
    expected13 = (
        "unsigned char XXDfile[] = {\n"
        "  0b01010100, 0b01000101, 0b01010011, 0b01010100, 0b01100001, 0b01100010,\n"
        "  0b01100011, 0b01100100, 0b00110000, 0b00111001, 0b00001010\n"
        "};\n"
        "unsigned int XXDfile_len = 11;"
    )
    record(upstream, "test13: -i -b binary C-include dump",
           out.decode("utf-8", "replace").rstrip("\n") == expected13)

    # ── upstream: testfiles/test14.sh (-e -cN) ───────────────────────────
    write_file("Xxdin", b"ABCDEF")
    rc, out, err = run(["-e", "-c6", "Xxdin"])
    lines = out.decode("utf-8", "replace").splitlines()
    record(upstream, "test14.1: -e -c6 little-endian",
           bool(lines) and lines[0] == "00000000: 44434241     4645  ABCDEF")
    write_file("Xxdin", b"ABCDEFGHI")
    rc, out, err = run(["-e", "-c9", "Xxdin"])
    lines = out.decode("utf-8", "replace").splitlines()
    record(upstream, "test14.2: -e -c9 little-endian",
           bool(lines) and lines[0] == "00000000: 44434241 48474645       49  ABCDEFGHI")

    # ── upstream: testfiles/test15.sh (-i from stdin) ────────────────────
    rc, out, err = run(["-i"], stdin=b"foo\n")
    record(upstream, "test15: -i from stdin",
           out.decode("utf-8", "replace").rstrip("\n") == "  0x66, 0x6f, 0x6f, 0x0a")

    # ── upstream: testfiles/test_c0.sh (-c 0 handling) ───────────────────
    write_file("hello.bin", b"hello world")
    rc, out, err = run(["-c", "0", "hello.bin"])
    record(upstream, "test_c0.1: -c 0 normal uses default columns",
           rc == 0 and b"6865 6c6c" in out)
    rc, out, err = run(["-c", "0", "-ps", "hello.bin"])
    record(upstream, "test_c0.2: -c 0 -ps emits a single hex line",
           out.decode("utf-8", "replace").rstrip("\n") == "68656c6c6f20776f726c64")
    rc, out, err = run(["-c", "0", "-b", "hello.bin"])
    record(upstream, "test_c0.3: -c 0 -b uses default columns",
           rc == 0 and b"01101000" in out)
    rc, out, err = run(["-c", "0", "-i", "hello.bin"])
    record(upstream, "test_c0.4: -c 0 -i uses default columns",
           rc == 0 and b"0x68" in out)
    rc, out, err = run(["-c", "0", "-e", "hello.bin"])
    record(upstream, "test_c0.5: -c 0 -e uses default columns",
           rc == 0 and b"6c6c6568" in out)
    write_file("large.bin", b"\x00" * 100)
    rc, out, err = run(["-c", "0", "-ps", "large.bin"])
    text = out.decode("utf-8", "replace").rstrip("\n")
    record(upstream, "test_c0.6: -c 0 -ps large file stays on one line",
           rc == 0 and "\n" not in text)
    record(upstream, "test_c0.7: -c 0 -ps 100 bytes = 200 hex chars", len(text) == 200)

    # ── upstream: make test little-endian padding ────────────────────────
    write_file("7.bin", b"ABCDEFG")
    rc, out, err = run(["-e", "-c", "8", "7.bin"])
    lines = out.decode("utf-8", "replace").splitlines()
    record(upstream, "make test: little-endian padding",
           bool(lines) and lines[0] == "00000000: 44434241   474645  ABCDEFG")

    # ── upstream: make test revert hexdump with CRLF ─────────────────────
    write_file("crlf.hex", b"00000000: 3132 3334\r\n00000004: 3536 3738\r\n")
    rc, out, err = run(["-r", "crlf.hex"])
    record(upstream, "make test: revert hexdump with CRLF line endings", out == b"12345678")

    # ── upstream: make test conversion + verification (round-trip) ───────
    sample = b"This is a test file"
    write_file("sample.bin", sample)
    rc, out, err = run(["sample.bin"])
    write_file("sample.hex", out)
    rc, out2, err = run(["-r", "sample.hex"])
    record(upstream, "make test: dump + revert round-trip", out2 == sample)

    # ── consumer: version + larger round-trip ────────────────────────────
    rc, out, err = run(["-v"])
    record(consumer, "consumer: -v reports tinyxxd 1.3.16",
           b"tinyxxd 1.3.16" in (out + err))

    data = bytes(range(256))
    write_file("rnd.bin", data)
    rc, out, err = run(["rnd.bin"])
    write_file("rnd.hex", out)
    rc, out2, err = run(["-r", "rnd.hex"])
    record(consumer, "consumer: 256-byte dump/revert round-trip", out2 == data)

    up_ok = sum(1 for _, ok in upstream if ok)
    cp_ok = sum(1 for _, ok in consumer if ok)
    failed = (len(upstream) - up_ok) + (len(consumer) - cp_ok)

    summary = {
        "upstream_passed": up_ok,
        "upstream_total": len(upstream),
        "consumer_passed": cp_ok,
        "consumer_total": len(consumer),
        "failed": failed,
    }
    with open(result_path, "w") as handle:
        json.dump(summary, handle)

    print("TINYXXD_RESULT up={upstream_passed} upt={upstream_total} "
          "cp={consumer_passed} cpt={consumer_total} failed={failed}".format(**summary))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
