#!/usr/bin/env python3
"""Driver for the enigma 1.3 consumer test (L0c test source).

Locates Crypt/Enigma.pm under the built package folder, runs the real API
test (test_crypt_enigma.pl) with PERL5LIB pointed at it, relays the TAP
output verbatim, and propagates the exit code. Finding no module file is
itself a failure (this is what the L1e destructive check relies on).
"""
import os
import shutil
import subprocess
import sys

PERL_CANDIDATES = (
    "/data/service/hnp/bin/perl",
    "/usr/bin/perl",
    "/usr/local/bin/perl",
)


def find_perl():
    found = shutil.which("perl")
    if found:
        return found
    for candidate in PERL_CANDIDATES:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def find_module_lib(pkg_folder):
    """Return the PERL5LIB root holding Crypt/Enigma.pm, or None."""
    target = os.path.join("Crypt", "Enigma.pm")
    for root, _dirs, files in os.walk(pkg_folder):
        if "Enigma.pm" in files:
            full = os.path.join(root, "Enigma.pm")
            if full.replace(os.sep, "/").endswith("Crypt/Enigma.pm"):
                prefix = full[: -len(target)].rstrip(os.sep)
                return prefix or root
    # Fallback: honour an already-exported PERL5LIB.
    perllib = os.environ.get("PERL5LIB", "")
    for entry in perllib.split(os.pathsep):
        if entry and os.path.isfile(os.path.join(entry, target)):
            return entry
    return None


def main():
    if len(sys.argv) < 2:
        print("FAIL: usage: test_enigma.py <package_folder>", file=sys.stderr)
        return 2
    pkg_folder = sys.argv[1]

    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 2

    perllib = find_module_lib(pkg_folder)
    if not perllib:
        print(
            "FAIL: Crypt/Enigma.pm not found under package folder "
            f"{pkg_folder}",
            file=sys.stderr,
        )
        return 1

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_crypt_enigma.pl")
    env = dict(os.environ)
    env["PERL5LIB"] = perllib + (os.pathsep + env["PERL5LIB"] if env.get("PERL5LIB") else "")

    proc = subprocess.run(
        [perl, script], capture_output=True, text=True, env=env, timeout=120
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    print(f"ENIGMA_DRIVER rc={proc.returncode} perllib={perllib}", flush=True)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
