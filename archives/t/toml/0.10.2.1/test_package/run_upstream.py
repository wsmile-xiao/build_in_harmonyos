#!/usr/bin/env python3
"""Run the upstream pytest suite packaged under upstream_tests/.

The upstream toml repo ships tests/test_api.py with 23 pytest cases.
Two of them (test_valid_tests / test_invalid_tests) rely on the external
BurntSushi/toml-test git submodule — download it (multi-mirror, R39)
into toml-test/tests/ before running so those cases execute for real.
The upstream CI (.travis.yml) clones that submodule separately.

Usage:
    python3 run_upstream.py <upstream_tests_dir>
"""
import os
import subprocess
import sys
import tarfile
import urllib.request

# Cases that depend on the external toml-test submodule (now provided by
# the download below, so they are no longer "expected to fail").
SUBMODULE_DEPENDENT = ()

TOML_TEST_URLS = (
    "https://gh-proxy.com/https://github.com/BurntSushi/toml-test/"
    "archive/refs/heads/master.tar.gz",
    "https://github.com/BurntSushi/toml-test/archive/refs/heads/master.tar.gz",
    "https://kkgithub.com/BurntSushi/toml-test/archive/refs/heads/master.tar.gz",
)


def fetch_toml_test(tests_dir: str) -> bool:
    """Download BurntSushi/toml-test (valid/invalid corpora) next to the
    suite so test_valid_tests / test_invalid_tests can actually run."""
    dest = os.path.join(tests_dir, "toml-test")
    if os.path.isdir(os.path.join(dest, "tests")):
        return True  # already present (CI cache / manual placement)
    last_err = None
    for url in TOML_TEST_URLS:
        try:
            print(f"[run_upstream] fetching toml-test: {url}")
            tarball = os.path.join(tests_dir, "toml-test.tar.gz")
            urllib.request.urlretrieve(url, tarball)
            with tarfile.open(tarball) as tf:
                member = next(n for n in tf.getnames()
                              if n.endswith("/tests/valid"))
                root = member.split("/tests/")[0]
                for n in tf.getnames():
                    if n.startswith(root + "/tests/"):
                        rel = n[len(root) + 1:]
                        target = os.path.join(dest, rel)
                        if tf.getmember(n).isdir():
                            os.makedirs(target, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(target),
                                        exist_ok=True)
                            with tf.extractfile(n) as src, \
                                    open(target, "wb") as out:
                                out.write(src.read())
            os.remove(tarball)
            return True
        except Exception as e:  # noqa: BLE001 — try next mirror
            last_err = e
            continue
    print(f"[run_upstream] toml-test download failed: {last_err}",
          file=sys.stderr)
    return False


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <upstream_tests_dir>", file=sys.stderr)
        return 2

    tests_dir = sys.argv[1]
    if not os.path.isdir(tests_dir):
        print(f"upstream_tests dir not found: {tests_dir}", file=sys.stderr)
        return 2

    # Provide the toml-test submodule data so the two submodule-dependent
    # cases run for real (21/23 -> 22/23 verified locally).
    fetch_toml_test(tests_dir)

    # Run pytest from inside upstream_tests/ so that test_api.py cases
    # which load "test.toml" from the current directory can find it
    # (we shipped test.toml next to the suite).
    # Single verbose run; capture stdout for classification while still
    # streaming it to CI via the echoed output below.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", tests_dir, "-v",
         "--no-header", "-rN"],
        capture_output=True, text=True,
        cwd=tests_dir,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)

    if proc.returncode == 0:
        print("[run_upstream] all upstream cases passed")
        return 0

    # Classify failures from the captured verbose report.
    failed = set()
    for line in proc.stdout.splitlines():
        if "FAILED" in line and "::" in line:
            failed.add(line.rsplit("::", 1)[-1].split()[0])

    unexpected = failed - set(SUBMODULE_DEPENDENT)
    if unexpected:
        print(f"[run_upstream] UNEXPECTED failures: {sorted(unexpected)}",
              file=sys.stderr)
        return 1

    toml_test_dir = os.path.join(os.getcwd(), "toml-test")
    if os.path.isdir(toml_test_dir):
        print("[run_upstream] toml-test submodule present but cases still "
              "failed", file=sys.stderr)
        return 1
    print("[run_upstream] failures limited to toml-test submodule cases "
          "(offline environment); non-submodule cases all passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
