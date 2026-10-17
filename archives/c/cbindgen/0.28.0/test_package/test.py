#!/usr/bin/env python3
"""Exercise the installed cbindgen CLI and generated Rust/C/C++ ABI."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--work", required=True)
    args = parser.parse_args()
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    fixture = work / "fixture"
    fixture.mkdir(exist_ok=True)
    source = Path(__file__).resolve().parent
    for name in ("point.rs", "consumer.c", "consumer.cpp", "Cargo.toml"):
        shutil.copyfile(source / name, fixture / name)
    records, assertions = [], []

    def check(name, condition):
        assertions.append({"name": name, "passed": bool(condition)})
        print(("[PASS] " if condition else "[FAIL] ") + name, flush=True)
        if not condition:
            raise AssertionError(name)

    def run(name, command, expected=0):
        command = list(map(str, command))
        print("[STEP] " + name + ": " + shlex.join(command), flush=True)
        result = subprocess.run(command, cwd=work, capture_output=True, timeout=120)
        for kind, data in (("stdout", result.stdout), ("stderr", result.stderr)):
            (work / (name + "." + kind)).write_bytes(data)
            print("[" + kind + "] " + (data.decode("utf-8", errors="replace") or "<empty>"), flush=True)
        print("[EXIT] " + str(result.returncode), flush=True)
        records.append({"name": name, "command": command, "exit_code": result.returncode})
        check(name + " exit=" + str(expected), result.returncode == expected)
        return result

    rc = 1
    try:
        binary = Path(args.binary).resolve()
        version = run("version", [binary, "--version"])
        check("exact version", version.stdout.strip() == b"cbindgen 0.28.0")
        header = work / "point.h"
        hpp = work / "point.hpp"
        run("generate-c", [binary, "--lang", "C", "--output", header,
                           "--depfile", work / "point.d", "--symfile", work / "point.sym",
                           fixture / "point.rs"])
        check("C declaration", "cbindgen_norm_sq" in header.read_text())
        check("dependency file", "point.rs" in (work / "point.d").read_text())
        check("symbols file", "cbindgen_norm_sq" in (work / "point.sym").read_text())
        run("generate-cpp-crate", [binary, "--lang", "C++", "--output", hpp,
                                  "--crate", "cbindgen-ffi-consumer", fixture])
        check("C++ C linkage", 'extern "C"' in hpp.read_text())
        run("verify-current", [binary, "--lang", "C", "--verify", "--output", header,
                               fixture / "point.rs"])
        cc = shlex.split(os.environ.get("CC", "clang"))
        cxx = shlex.split(os.environ.get("CXX", "clang++"))
        library = work / "libpoint.a"
        run("rust-library", [os.environ.get("RUSTC", "rustc"), "--edition=2021",
                             "--crate-type", "staticlib", fixture / "point.rs", "-o", library])
        run("link-c", cc + ["-std=c11", "-Wall", "-Werror", "-I", str(work),
                            str(fixture / "consumer.c"), str(library), "-lm", "-o", str(work / "consumer-c")])
        c_result = run("run-c", [work / "consumer-c"])
        check("C business result", b"C_FFI_RESULT=25" in c_result.stdout)
        run("link-cpp", cxx + ["-std=c++17", "-Wall", "-Werror", "-I", str(work),
                               str(fixture / "consumer.cpp"), str(library), "-lm", "-o", str(work / "consumer-cpp")])
        cpp_result = run("run-cpp", [work / "consumer-cpp"])
        check("C++ business result", b"CPP_FFI_RESULT=169" in cpp_result.stdout)
        (fixture / "bad.rs").write_text("pub struct Broken {", encoding="utf-8")
        bad = run("invalid-rust", [binary, "--lang", "C", fixture / "bad.rs"], expected=1)
        check("invalid Rust diagnostic", bool(bad.stderr.strip()))
        rc = 0
    except (OSError, AssertionError, subprocess.SubprocessError) as error:
        print("[FAIL] " + str(error), flush=True)
    finally:
        report = {"exit_code": rc, "assertions": assertions, "commands": records,
                  "passed": sum(item["passed"] for item in assertions),
                  "total": len(assertions),
                  "hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in work.iterdir() if p.is_file() and p.name != "result.json"}}
        (work / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
