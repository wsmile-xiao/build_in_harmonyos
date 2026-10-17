#!/usr/bin/env python3
"""Execute package tests locally and, when requested, on an HDC-connected target."""
import argparse
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def native(consumer, theme, ohos):
    manifest = HERE / "expected.tsv"
    subprocess.run([str(consumer), "--check", str(theme), str(manifest)], check=True)
    with tempfile.TemporaryDirectory(prefix="breeze-negative-") as empty:
        rejected = subprocess.run([str(consumer), "--check", empty, str(manifest)], capture_output=True)
        if rejected.returncode != 1 or b"Invalid resource:" not in rejected.stderr:
            raise RuntimeError("Missing package must fail in the consumer")
        print("[ok] target rejects missing resources", flush=True)
        broken = Path(empty) / "corrupted"
        shutil.copytree(theme, broken)
        (broken / "theme.txt").write_bytes(b"broken theme\n")
        rejected = subprocess.run([str(consumer), "--check", str(broken), str(manifest)], capture_output=True)
        if rejected.returncode != 1 or b"Invalid resource: theme.txt" not in rejected.stderr:
            raise RuntimeError("Corrupted package must fail in the consumer")
        print("[ok] target rejects corrupted resources", flush=True)
        if ohos:
            subprocess.run([str(consumer), "--sandbox", str(theme), str(manifest)], check=True,
                           env={**os.environ, "TMPDIR": empty})


def hdc_run(hdc, target, consumer, theme):
    prefix = [hdc] + (["-t", target] if target else [])
    remote = "/data/local/tmp/breeze-grub-6.7.2-" + os.urandom(6).hex()

    def invoke(args, timeout=180):
        result = subprocess.run(prefix + args, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout, check=True)
        output = result.stdout + result.stderr
        print(output, end="", flush=True)
        if re.search(r"(?im)^\[(?:Fail|FAIL|F)\]|Error opening file", output):
            raise RuntimeError("HDC transport operation failed")
        return output

    system = invoke(["shell", "param get const.ohos.fullname"])
    if not re.search(r"(?:OpenHarmony|HarmonyOS)", system):
        raise RuntimeError("The target does not identify as HarmonyOS/OpenHarmony")
    invoke(["shell", f"mkdir -p {remote}"])
    invoke(["file", "send", str(consumer), remote + "/test_breeze"])
    invoke(["file", "send", str(theme), remote + "/breeze"])
    invoke(["file", "send", str(HERE / "expected.tsv"), remote + "/expected.tsv"])
    script = "\n".join([
        "#!/bin/sh", "set -eu", f"cd {shlex.quote(remote)}",
        "chmod 755 test_breeze", "export TMPDIR=" + shlex.quote(remote),
        "./test_breeze --check breeze expected.tsv",
        "mkdir empty",
        "if ./test_breeze --check empty expected.tsv > negative.log 2>&1; then exit 1; "
        "else rc=$?; test \"$rc\" = 1; fi",
        "grep -q 'Invalid resource:' negative.log",
        "echo '[ok] target rejects missing resources'",
        "cp -R breeze broken",
        "printf 'broken theme\\n' > broken/theme.txt",
        "if ./test_breeze --check broken expected.tsv > corrupt.log 2>&1; then exit 1; "
        "else rc=$?; test \"$rc\" = 1; fi",
        "grep -q 'Invalid resource: theme.txt' corrupt.log",
        "echo '[ok] target rejects corrupted resources'",
        "./test_breeze --sandbox breeze expected.tsv",
        "echo '__BREEZE_ALL_PASSED__'", "",
    ])
    with tempfile.TemporaryDirectory(prefix="breeze-hdc-") as temporary:
        path = Path(temporary) / "run.sh"
        path.write_text(script, encoding="utf-8", newline="\n")
        invoke(["file", "send", str(path), remote + "/run.sh"])
    output = invoke(["shell", f"sh {remote}/run.sh; rc=$?; echo __BREEZE_RC__=$rc; exit $rc"], 300)
    required = ["__BREEZE_ALL_PASSED__", "[ok] target resources: 23/23 byte counts and CRC32",
                "[ok] target rejects missing resources",
                "[ok] target rejects corrupted resources",
                "[ok] HarmonyOS TMPDIR copy/rename/reopen: 23/23 resources"]
    if re.findall(r"(?m)^__BREEZE_RC__=(\d+)\s*$", output) != ["0"] or any(
            output.count(marker) != 1 for marker in required):
        raise RuntimeError(f"Target verification failed; evidence retained at {remote}")
    print(f"[ok] HarmonyOS target evidence: {remote}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--ohos", action="store_true")
    parser.add_argument("--hdc")
    parser.add_argument("--target", default="")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(HERE / "test_resources.py"), str(args.package)], check=True)
    theme = args.package / "share" / "grub" / "themes" / "breeze"
    if args.hdc:
        hdc_run(args.hdc, args.target, args.consumer.resolve(), theme)
    else:
        native(args.consumer.resolve(), theme, args.ohos)
