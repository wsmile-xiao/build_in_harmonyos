#!/usr/bin/env python3
"""Run the QtBase consumer binaries with identical local/device assertions."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import time


def run_case(command, expected_code, directory, name, timeout=120, tmpdir=None):
    print(f"[STEP] {name}: {shlex.join(command)}", flush=True)
    started = time.monotonic()
    timed_out = False
    env = None
    if tmpdir is not None:
        # CI workers share one TMPDIR across every build; a stale
        # foreign-owned $TMPDIR/runtime-<uid> directory makes QStandardPaths
        # reject the numeric-UID runtime fallback (Build #61061). Scope TMPDIR
        # to this run's own directory so the fallback is created fresh and
        # owned by the process; XDG_RUNTIME_DIR stays unset so the fallback
        # path is still exercised.
        env = dict(os.environ)
        env["TMPDIR"] = str(tmpdir)
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout, env=env)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr = 124, error.stdout or b"", error.stderr or b""
        timed_out = True
    except OSError as error:
        code, stdout, stderr = 127, b"", str(error).encode("utf-8")
    for stream, data in (("stdout", stdout), ("stderr", stderr)):
        (directory / f"{name}.{stream}.log").write_bytes(data)
        print(f"[{stream.upper()}]\n{data.decode('utf-8', errors='replace') or '<empty>'}",
              flush=True)
    passed = code == expected_code and not timed_out
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: exit={code}, expected={expected_code}",
          flush=True)
    return {"name": name, "command": command, "exit_code": code,
            "expected_exit_code": expected_code, "passed": passed,
            "timeout": timed_out, "seconds": round(time.monotonic() - started, 3),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest()}


def check_aarch64(path):
    with path.open("rb") as stream:
        header = stream.read(20)
    return (len(header) == 20 and header[:6] == b"\x7fELF\x02\x01"
            and struct.unpack_from("<H", header, 18)[0] == 183)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin-dir", type=Path, required=True)
    parser.add_argument("--log-dir", type=Path, required=True)
    parser.add_argument("--wayland", action="store_true")
    parser.add_argument("--require-aarch64", action="store_true")
    args = parser.parse_args(argv)
    args.log_dir.mkdir(parents=True, exist_ok=True)
    qt = args.bin_dir.resolve() / "test_qtbase"
    codegen = args.bin_dir.resolve() / "test_wayland_codegen"
    result = {"wayland_requested": args.wayland, "font_directory": os.environ.get("QT_QPA_FONTDIR"), "cases": []}
    try:
        for binary in (qt, codegen):
            if not binary.is_file():
                raise RuntimeError(f"Missing test executable: {binary}")
            if args.require_aarch64 and not check_aarch64(binary):
                raise RuntimeError(f"Expected ELF64 AArch64: {binary}")
        commands = [("offscreen", [str(qt), "--offscreen"], 0),
                    ("system", [str(qt), "--system"], 0),
                    ("codegen", [str(codegen)], 0),
                    ("negative-control", [str(qt), "--negative-control"], 97),
                    ("invalid-mode", [str(qt), "--invalid-mode"], 65)]
        scoped_tmpdir = args.log_dir / "scoped-tmp"
        scoped_tmpdir.mkdir(parents=True, exist_ok=True)
        for name, command, expected in commands:
            result["cases"].append(run_case(command, expected, args.log_dir, name,
                                            tmpdir=scoped_tmpdir))
        if result["font_directory"]:
            result["cases"].append(run_case([str(qt), "--fonts"], 0, args.log_dir, "fonts"))
        else:
            print("[SKIP] font assets: QT_QPA_FONTDIR is unset", flush=True)
        if args.wayland:
            # Preserve the desktop's real XDG_RUNTIME_DIR and WAYLAND_DISPLAY.
            result["cases"].append(run_case([str(qt), "--wayland"], 0,
                                            args.log_dir, "wayland"))
        else:
            print("[SKIP] real Wayland window: not requested", flush=True)
        result["passed"] = all(case["passed"] for case in result["cases"])
    except (OSError, RuntimeError) as error:
        result.update(passed=False, error=str(error))
        print(f"[FAIL] {error}", flush=True)
    (args.log_dir / "consumer-result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
