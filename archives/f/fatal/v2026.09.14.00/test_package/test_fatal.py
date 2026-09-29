#!/usr/bin/env python3
"""fatal v2026.09.14.00 consumer test driver (HarmonyOS PC / aarch64).

Compiles and runs the consumer programs shipped next to this file against
the *installed* fatal package.  fatal is header-only, so the consumer
surface is exactly `<package>/include` — the driver refuses to run if the
headers are missing, which is what makes the destructive negative check
(L1e) meaningful.

Strictness mirrors the upstream harness: -Wall -Werror -Wextra -std=c++17.
OHOS notes: /tmp is a read-only erofs, so the driver works inside its own
directory, and subprocess needs absolute executable paths (posix_spawn does
not search PATH).
"""
import os
import shutil
import subprocess
import sys

CXX_CANDIDATES = [
    "/data/service/hnp/bin/clang++",
    "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++",
    "/usr/bin/clang++",
]

FLAGS = [
    "-O0", "-g", "-pthread",
    "-ftemplate-depth-1024", "-ftemplate-backtrace-limit=0",
    "-ferror-limit=1",
    "-Wall", "-Werror", "-Wextra",
    "-std=c++17",
]

CONSUMER_TESTS = [
    ("consumer_api_test.cpp",
     "fatal::list/size/reverse/push_front + runtime fatal::foreach traversal"),
    ("rope_iterator_test.cpp",
     "fatal::rope const_iterator (patch 0001) — -Werror clean + runtime walk"),
    ("ohos_libcxx_surface_test.cpp",
     "public fatal/type/ header surface under OHOS libc++ (patch 0002 path)"),
]


def find_cxx():
    for candidate in CXX_CANDIDATES:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    found = shutil.which("clang++")
    if found:
        return found
    return None


def main():
    if len(sys.argv) < 2:
        print("usage: test_fatal.py <package_folder> [build_folder]",
              file=sys.stderr)
        return 2

    pkg = sys.argv[1]
    include = os.path.join(pkg, "include")
    probe = os.path.join(include, "fatal", "type", "list.h")

    print("[fatal consumer] package  : %s" % pkg)
    if not os.path.isfile(probe):
        print("[fatal consumer] FAIL: installed header missing: %s" % probe)
        return 1
    print("[fatal consumer] header   : %s (present)" % probe)

    cxx = find_cxx()
    if not cxx:
        print("[fatal consumer] FAIL: no C++ compiler found")
        return 1
    print("[fatal consumer] compiler : %s" % cxx)

    here = os.path.dirname(os.path.abspath(__file__))
    # build artifacts go to the Conan test build folder (or ./_build when the
    # driver is run by hand) — /tmp is a read-only erofs on HarmonyOS PC
    work = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] \
        else os.path.join(here, "_build")
    work = os.path.join(work, "fatal-consumer")
    os.makedirs(work, exist_ok=True)

    failures = []
    for source, description in CONSUMER_TESTS:
        binary = os.path.join(work, source[:-len(".cpp")])
        cmd = [cxx] + FLAGS + ["-I", include, os.path.join(here, source),
                               "-o", binary]
        print("[fatal consumer] compiling %s (%s)" % (source, description))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0 or not os.path.exists(binary):
            print("[fatal consumer] FAIL compile %s\n%s"
                  % (source, (proc.stdout + proc.stderr)[-1200:]))
            failures.append(source)
            continue

        print("[fatal consumer] running ./%s" % source[:-len(".cpp")])
        run = subprocess.run([binary], capture_output=True, text=True,
                             timeout=900, cwd=work)
        output = ((run.stdout or "") + (run.stderr or "")).strip()
        for line in output.splitlines():
            print("[fatal consumer]   %s" % line)
        if run.returncode != 0:
            print("[fatal consumer] FAIL run %s (exit %d)"
                  % (source, run.returncode))
            failures.append(source)

    total = len(CONSUMER_TESTS)
    if failures:
        print("[fatal consumer] FAILED %d/%d: %s"
              % (len(failures), total, ", ".join(failures)))
        return 1

    print("[fatal consumer] fatal v2026.09.14.00 consumer tests OK: %d/%d passed"
          % (total, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
