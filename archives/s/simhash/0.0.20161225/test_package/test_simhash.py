#!/usr/bin/env python3
"""CLI harness for the installed simhash tool.

Generates similarity hashes for a small deterministic corpus and checks the
comparison semantics:
  * identical files            -> 1.0
  * one word changed           -> positive score (> 0.5 in practice)
  * unrelated content          -> 0.0
  * different -f/-s parameters -> different hash files
  * comparison never fails the process (documented exit code 0)

Usage: test_simhash.py <path-to-simhash> <package-folder> <workdir> <result-json>
"""
import json
import os
import subprocess
import sys


def run_text(argv, cwd):
    """Run a command whose stdout is textual (the -c comparison value)."""
    return subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, errors="replace")


def run_to_file(argv, cwd, path):
    """Run a command whose stdout is a binary hash and must go straight to a
    file: the hash bytes are not valid UTF-8, so they cannot be piped."""
    with open(path, "wb") as handle:
        return subprocess.run(argv, cwd=cwd, stdout=handle,
                              stderr=subprocess.PIPE)


def main():
    binary, package_folder, workdir, result_file = sys.argv[1:5]
    os.makedirs(workdir, exist_ok=True)

    checks = []
    info = {}

    def check(name, condition, detail=""):
        checks.append({"name": name, "passed": bool(condition), "detail": detail})
        print("  {} {}".format("ok  " if condition else "FAIL", name))

    # ---- corpus ---------------------------------------------------------
    corpus = {
        "a.txt": "the quick brown fox jumps over the lazy dog\n" * 8,
        "b.txt": "the quick brown fox jumps over the lazy cat\n" * 8,
        "c.txt": "completely different content about compilers and kernels\n" * 8,
    }
    for name, content in corpus.items():
        with open(os.path.join(workdir, name), "w", encoding="utf-8") as handle:
            handle.write(content)

    # ---- tool availability ---------------------------------------------
    check("installed simhash binary exists", os.path.isfile(binary), binary)
    if not os.path.isfile(binary):
        summary = {"passed": 0, "failed": 1, "total": 1, "checks": checks, "info": info}
        with open(result_file, "w", encoding="utf-8") as handle:
            json.dump(summary, handle)
        return 1

    def make_hash(source, target, features="64", shingles="4"):
        path = os.path.join(workdir, target)
        result = run_to_file([binary, "-f", features, "-s", shingles, source],
                             workdir, path)
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        return result, size

    def compare(left, right):
        result = run_text([binary, "-c", left, right], workdir)
        text = result.stdout.strip()
        try:
            value = float(text)
        except ValueError:
            value = None
        return result, value, text

    # ---- hash generation ------------------------------------------------
    result_a, size_a = make_hash("a.txt", "a.sim")
    result_b, size_b = make_hash("b.txt", "b.sim")
    result_c, size_c = make_hash("c.txt", "c.sim")
    info["hash_size"] = size_a
    check("simhash -f 64 -s 4 writes a non-empty hash file",
          result_a.returncode == 0 and size_a > 0,
          "rc={} size={}".format(result_a.returncode, size_a))
    check("every corpus file produces a non-empty hash",
          result_a.returncode == 0 and result_b.returncode == 0
          and result_c.returncode == 0 and size_a > 0 and size_b > 0 and size_c > 0,
          "sizes {} {} {}".format(size_a, size_b, size_c))

    # ---- comparison semantics -------------------------------------------
    result, value, text = compare("a.sim", "a.sim")
    info["identical"] = text
    check("identical files compare to 1.0",
          result.returncode == 0 and value == 1.0, text)

    result, value, text = compare("a.sim", "b.sim")
    info["similar"] = text
    check("one word different compares to a positive score",
          result.returncode == 0 and value is not None and value > 0.5, text)

    result, value, text = compare("a.sim", "c.sim")
    info["different"] = text
    check("unrelated content compares to 0.0",
          result.returncode == 0 and value == 0.0, text)

    check("comparison exits 0 even for unrelated files", result.returncode == 0,
          "rc={}".format(result.returncode))

    # ---- parameters change the hash -------------------------------------
    _, size_256 = make_hash("a.txt", "a256.sim", features="256", shingles="8")
    with open(os.path.join(workdir, "a.sim"), "rb") as handle:
        hash_64 = handle.read()
    with open(os.path.join(workdir, "a256.sim"), "rb") as handle:
        hash_256 = handle.read()
    check("different -f/-s parameters produce a different hash",
          size_256 > 0 and hash_64 != hash_256,
          "{} vs {} bytes".format(len(hash_64), len(hash_256)))

    # ---- man page --------------------------------------------------------
    man_page = os.path.join(package_folder, "share", "man", "man1", "simhash.1")
    check("man page installed as share/man/man1/simhash.1",
          os.path.isfile(man_page), man_page)

    passed = sum(1 for item in checks if item["passed"])
    failed = len(checks) - passed
    summary = {"passed": passed, "failed": failed, "total": len(checks),
               "checks": checks, "info": info}
    with open(result_file, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=1)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
