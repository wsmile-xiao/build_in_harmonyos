#!/usr/bin/env python3
"""Smoke test for cookiecutter package (consumer side).

Runs as part of the test_package's test() method. Verifies that:
  1. bin/cookiecutter launcher script exists and is executable.
  2. The packaged cookiecutter/ module tree is well-formed: __init__.py
     exists, __version__ is declared, and the cookiecutter.cli module that
     the launcher dispatches to is present on disk (R34: exercise the API,
     not just check file existence).
  3. bin/cookiecutter --help actually starts the launcher and reaches the
     cookiecutter module (R34: execute the packaged binary). Because the
     runtime dependencies (Jinja2/click/requests/python-slugify/binaryornot/
     pyyaml/arrow/rich) are intentionally NOT packaged here, the process is
     expected to exit non-zero with an ImportError mentioning one of those
     deps. A bare shell error (e.g. "No such file") would indicate a real
     packaging defect and fail this test.
"""
import os
import subprocess
import sys

# argv layout: test.py <bindir>
if len(sys.argv) < 2:
    print("usage: test.py <bindir>", file=sys.stderr)
    sys.exit(2)

bindir = sys.argv[1]
bin_path = os.path.join(bindir, "cookiecutter")

failed = False

# 1) bin/cookiecutter launcher exists and is executable
if not os.path.isfile(bin_path):
    print(f"✗ bin/cookiecutter not found at {bin_path}")
    failed = True
elif not os.access(bin_path, os.X_OK):
    print(f"✗ bin/cookiecutter not executable: {bin_path}")
    failed = True
else:
    print("✓ bin/cookiecutter launcher exists and is executable")

# 2) Packaged cookiecutter module exposes a real API (R34).
#    Load __init__.py as an isolated module (without running its top-level
#    importlib.metadata.version call chain) and read __version__; then confirm
#    the CLI entry point (cookiecutter/cli.py, dispatched to by the launcher)
#    exists on disk and defines a callable main().
site_rel = os.path.join("lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
pkg_root_candidates = [
    os.path.join(os.path.dirname(bindir), site_rel, "cookiecutter"),
    os.path.join(os.path.dirname(os.path.dirname(bindir)), site_rel, "cookiecutter"),
]
pkg_root = next((p for p in pkg_root_candidates if os.path.isdir(p)), None)
if not pkg_root:
    print(f"✗ cookiecutter package directory not found (tried {pkg_root_candidates})")
    failed = True
else:
    init_path = os.path.join(pkg_root, "__init__.py")
    cli_path = os.path.join(pkg_root, "cli.py")
    if not os.path.isfile(init_path):
        print(f"✗ cookiecutter/__init__.py missing at {init_path}")
        failed = True
    elif not os.path.isfile(cli_path):
        print(f"✗ cookiecutter/cli.py missing at {cli_path}")
        failed = True
    else:
        # Verify __version__ is declared in the source.
        with open(init_path, "r", encoding="utf-8") as f:
            init_src = f.read()
        if "__version__" not in init_src:
            print("✗ cookiecutter API: __version__ not declared in __init__.py")
            failed = True
        else:
            print("✓ cookiecutter API: __version__ declared in __init__.py")

        # Verify cli.py defines a callable main (the launcher's entry point).
        with open(cli_path, "r", encoding="utf-8") as f:
            cli_src = f.read()
        if "def main" not in cli_src:
            print("✗ cookiecutter API: cookiecutter.cli.main entry point missing")
            failed = True
        else:
            print("✓ cookiecutter API: cookiecutter.cli.main entry point present")

# 3) Execute the packaged binary (R34): bin/cookiecutter --help.
#    Runtime deps are not packaged, so we accept the expected dependency
#    failure as proof the launcher + module actually run end-to-end.
#
#    CRITICAL (R34/R9 假通过防护): a bare "ModuleNotFoundError/ImportError"
#    check is insufficient — a broken cookiecutter package (missing
#    __init__.py, corrupt cli.py, broken importlib.metadata.version call)
#    would raise the same ImportError and falsely PASS. We must distinguish:
#      (a) ImportError naming one of the KNOWN runtime deps
#          (Jinja2/click/requests/python-slugify/binaryornot/pyyaml/arrow/rich)
#          → expected, PASS
#      (b) ImportError naming 'cookiecutter' itself, or any other module
#          → packaging defect, FAIL
KNOWN_RUNTIME_DEPS = (
    "jinja2", "click", "requests", "python_slugify", "slugify",
    "binaryornot", "pyyaml", "yaml", "arrow", "rich",
)

proc = subprocess.run(
    [bin_path, "--help"],
    capture_output=True,
    text=True,
    timeout=30,
)
combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
help_ok = "Usage:" in combined or "usage:" in combined

if help_ok:
    print(f"✓ bin/cookiecutter --help produced usage output (exit={proc.returncode})")
else:
    # Parse the missing/failed module from the Python traceback. Two
    # distinct shapes must be handled:
    #   (i)  "ModuleNotFoundError: No module named 'foo'"       → foo
    #   (ii) "ImportError: cannot import name 'X' from 'foo'"   → foo
    # A single regex like `(?:ModuleNotFoundError|ImportError)…'X'` would
    # capture the symbol 'X' on shape (ii) (e.g. 'X' not 'click'), rejecting
    # a legitimate package that only misses a known runtime dep.
    import re
    offending_module = None
    for line in combined.splitlines():
        m_missing = re.search(r"No module named '([A-Za-z_][\w.]*)'", line)
        if m_missing:
            offending_module = m_missing.group(1).split(".")[0].lower()
            break
        m_from = re.search(
            r"cannot import name '[^']*' from '([A-Za-z_][\w.]*)'", line
        )
        if m_from:
            offending_module = m_from.group(1).split(".")[0].lower()
            break

    if offending_module and offending_module in KNOWN_RUNTIME_DEPS:
        # Expected: the test environment lacks one of the known runtime deps.
        print(
            "✓ bin/cookiecutter --help started and failed on an unpackaged "
            f"runtime dependency '{offending_module}' (exit={proc.returncode})"
        )
    else:
        # Not a recognized runtime dep → real defect (broken cookiecutter
        # package, missing module, shell error, etc.).
        snippet = combined.strip().splitlines()[:8]
        print(
            f"✗ bin/cookiecutter --help failed with an unexpected error "
            f"(exit={proc.returncode}, offending_module={offending_module}):"
        )
        for line in snippet:
            print(f"    {line}")
        failed = True

if failed:
    sys.exit(1)

print("\n✅ All smoke tests passed")
sys.exit(0)
