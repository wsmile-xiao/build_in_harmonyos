#!/usr/bin/env python3
"""Validate the packaged PARI data, then exercise the target-side consumer."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zlib


HERE = Path(__file__).resolve().parent


def check_data(datadir, expected):
    data = datadir / "seadata"
    actual = {p.name for p in data.iterdir() if p.is_file()}
    if actual != set(expected):
        raise RuntimeError(f"Data inventory mismatch: {actual ^ set(expected)}")
    for name, record in expected.items():
        raw = (data / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise RuntimeError(f"SHA256 mismatch: {name}")
        if name.endswith(".gz"):
            plain = gzip.decompress(raw)
            value = json.loads(plain)
            level = record["level"]
            if (len(value) != 3 or value[0] != level or value[1] != "A"
                    or len(value[2]) != level + 2 or value[2][0] != 1):
                raise RuntimeError(f"Atkin polynomial structure mismatch: {name}")
            for coefficient in value[2]:
                if type(coefficient) is int:
                    continue
                if (not isinstance(coefficient, list) or not coefficient
                        or any(type(v) is not int for v in coefficient)):
                    raise RuntimeError(f"Invalid coefficient: {name}")
            if (len(plain) != record["bytes"]
                    or zlib.crc32(plain) != int(record["crc32"], 16)):
                raise RuntimeError(f"Uncompressed data mismatch: {name}")
            print(f"[ok] content {name}", flush=True)
    print("[ok] package inventory: 44 polynomials + upstream README", flush=True)


def run_native(consumer, datadir, expected, ohos):
    for name, record in expected.items():
        if not name.endswith(".gz"):
            continue
        plain = gzip.decompress((datadir / "seadata" / name).read_bytes())
        command = [str(consumer), str(record["level"]), str(record["bytes"]), record["crc32"]]
        subprocess.run(command, input=plain, check=True)
    first = expected["sea503.gz"]
    command = [str(consumer), "503", str(first["bytes"]), first["crc32"]]
    rejected = subprocess.run(command, input=b"[503, \"A\", [1]]\n", capture_output=True)
    if rejected.returncode == 0:
        raise RuntimeError("Consumer accepted truncated data")
    print("[ok] negative test: truncated data rejected", flush=True)
    if ohos:
        # Native workers need not ship the developer-shell `param` command.
        # The consumer's SDK-defined __OHOS__ guard rejects non-OHOS builds.
        with tempfile.TemporaryDirectory(prefix="pari-seadata-") as temporary:
            plainfile = Path(temporary) / "sea503"
            plainfile.write_bytes(gzip.decompress((datadir / "seadata" / "sea503.gz").read_bytes()))
            subprocess.run([str(consumer), "--sandbox", str(plainfile),
                            str(first["bytes"]), first["crc32"]], check=True,
                           env={**os.environ, "TMPDIR": temporary})


def run_hdc(hdc, target, consumer, datadir, expected):
    prefix = [hdc] + (["-t", target] if target else [])
    remote = "/data/local/tmp/pari-seadata-big-20170418-" + os.urandom(4).hex()

    def invoke(args, timeout=300):
        result = subprocess.run(prefix + args, capture_output=True, text=True,
                                timeout=timeout, check=True)
        text = result.stdout + result.stderr
        print(text, end="", flush=True)
        if re.search(r"(?im)^\[(?:Fail|FAIL|F)\]|Error opening file", text):
            raise RuntimeError("HDC operation failed")
        return text

    system = invoke(["shell", "param get const.ohos.fullname"])
    if not re.search(r"(?:OpenHarmony|HarmonyOS)", system):
        raise RuntimeError("Connected target is not HarmonyOS/OpenHarmony")
    invoke(["shell", f"mkdir -p {remote}"])
    invoke(["file", "send", str(consumer), remote + "/test_seadata"])
    invoke(["file", "send", str(datadir / "seadata"), remote + "/seadata"])
    lines = ["#!/bin/sh", "set -eu", "set -o pipefail", f"cd {remote}",
             "chmod 755 ./test_seadata", "export TMPDIR=" + remote]
    for name, record in expected.items():
        if name.endswith(".gz"):
            lines.append(f"gzip -dc seadata/{name} | ./test_seadata {record['level']} "
                         f"{record['bytes']} {record['crc32']}")
    first = expected["sea503.gz"]
    lines.extend([
        "if printf 'broken data' | ./test_seadata 503 " + str(first["bytes"]) + " "
        + first["crc32"] + "; then echo 'negative test failed'; exit 1; fi",
        "echo '[ok] negative test: truncated data rejected'",
        "gzip -dc seadata/sea503.gz > sea503",
        "./test_seadata --sandbox sea503 " + str(first["bytes"]) + " " + first["crc32"],
        "echo '__PARI_SEADATA_ALL_PASSED__'",
    ])
    with tempfile.TemporaryDirectory(prefix="pari-seadata-hdc-") as temporary:
        script = Path(temporary) / "run.sh"
        script.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        invoke(["file", "send", str(script), remote + "/run.sh"])
    output = invoke(["shell", f"sh {remote}/run.sh; rc=$?; echo __PARI_REMOTE_RC__=$rc; exit $rc"], 900)
    if (re.findall(r"(?m)^__PARI_REMOTE_RC__=(\d+)\s*$", output) != ["0"]
            or "__PARI_SEADATA_ALL_PASSED__" not in output
            or output.count("[ok] target polynomial") != 44
            or "[ok] HarmonyOS sandbox relocation" not in output):
        raise RuntimeError(f"Target tests did not all pass; evidence retained at {remote}")
    print(f"[ok] target evidence: {remote}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("datadir", type=Path)
    parser.add_argument("--consumer", type=Path)
    parser.add_argument("--ohos", action="store_true")
    parser.add_argument("--hdc")
    parser.add_argument("--target", default="")
    args = parser.parse_args()
    expected = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
    check_data(args.datadir, expected)
    if args.consumer:
        if args.hdc:
            run_hdc(args.hdc, args.target, args.consumer.resolve(), args.datadir, expected)
        else:
            run_native(args.consumer.resolve(), args.datadir, expected, args.ohos)


if __name__ == "__main__":
    main()
