#!/usr/bin/env python3
"""CLI + layout harness for the installed libmoe package.

Checks the installed artefacts (library, public headers, man page) and drives
the installed ``mbconv`` tool on deterministic inputs:
  * ASCII / UTF-8 pass-through must be byte identical,
  * ``-c ASCII`` conversion must succeed and keep the ASCII payload,
  * ``-t <file>`` must write what stdout would have produced,
  * the tool must accept input on stdin.

Usage: test_libmoe.py <package-folder> <workdir> <result-json>
"""
import json
import os
import subprocess
import sys


def run(argv, cwd, data=None):
    return subprocess.run(argv, cwd=cwd, input=data, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, errors="replace")


def main():
    package_folder, workdir, result_file = sys.argv[1:4]
    os.makedirs(workdir, exist_ok=True)

    binary = os.path.join(package_folder, "bin", "mbconv")
    checks = []
    info = {}

    def check(name, condition, detail=""):
        checks.append({"name": name, "passed": bool(condition), "detail": detail})
        print("  {} {}".format("ok  " if condition else "FAIL", name))

    # ---- installed layout -------------------------------------------------
    check("installed bin/mbconv exists", os.path.isfile(binary), binary)
    if not os.path.isfile(binary):
        with open(result_file, "w", encoding="utf-8") as handle:
            json.dump({"passed": 0, "failed": 1, "total": 1, "checks": checks,
                       "info": info}, handle)
        return 1

    library = os.path.join(package_folder, "lib", "libmoe.a")
    check("static library lib/libmoe.a installed", os.path.isfile(library), library)

    header = os.path.join(package_folder, "include", "moe", "mb.h")
    check("public header include/moe/mb.h installed", os.path.isfile(header), header)

    man_page = os.path.join(package_folder, "share", "man", "man1", "mbconv.1.gz")
    if not os.path.isfile(man_page):
        man_page = os.path.join(package_folder, "share", "man", "man1", "mbconv.1")
    check("man page installed", os.path.isfile(man_page), man_page)

    # ---- deterministic conversions ---------------------------------------
    sample = "The quick brown fox.\nSecond line with ASCII only.\n"

    result = run([binary], workdir, data=sample)
    info["passthrough"] = result.stdout
    check("ASCII input passes through unchanged",
          result.returncode == 0 and result.stdout == sample,
          "rc={}".format(result.returncode))

    result = run([binary, "-cs", "UTF-8"], workdir, data=sample)
    check("explicit UTF-8 charset keeps ASCII payload",
          result.returncode == 0 and result.stdout == sample,
          "rc={}".format(result.returncode))

    result = run([binary, "-c", "ASCII"], workdir, data=sample)
    check("`-c ASCII` conversion succeeds and preserves the payload",
          result.returncode == 0 and result.stdout == sample,
          "rc={}".format(result.returncode))

    out_file = os.path.join(workdir, "out.txt")
    result = run([binary, "-t", out_file], workdir, data=sample)
    written = ""
    if os.path.isfile(out_file):
        with open(out_file, "r", encoding="utf-8", errors="replace") as handle:
            written = handle.read()
    info["to_file"] = written
    check("`-t <file>` writes the same bytes as stdout",
          result.returncode == 0 and written == sample,
          "rc={}".format(result.returncode))

    result = run([binary, "-c", "ASCII", "-"], workdir, data=sample)
    check("reading from an explicit '-' input works",
          result.returncode == 0 and result.stdout == sample,
          "rc={}".format(result.returncode))

    result = run([binary, "-h"], workdir)
    check("`-h` prints the usage summary",
          "mbconv" in (result.stdout + result.stderr) and
          "libmoe" in (result.stdout + result.stderr),
          "rc={}".format(result.returncode))

    passed = sum(1 for item in checks if item["passed"])
    failed = len(checks) - passed
    with open(result_file, "w", encoding="utf-8") as handle:
        json.dump({"passed": passed, "failed": failed, "total": len(checks),
                   "checks": checks, "info": info}, handle, indent=1)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
