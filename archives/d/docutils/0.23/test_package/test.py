#!/usr/bin/env python3
"""docutils test_package smoke test.

Called by test_package/conanfile.py test() with:
  DOCUTILS_SITE_PACKAGES — path to the docutils site-packages directory
  DOCUTILS_BIN — path to the bin/ directory with entry-point scripts

Verification strategy (two levels):
  1) Package integrity (hard assert):
     - docutils/__init__.py exists and __version__ == "0.23"
     - docutils/core.py exists
  2) Functional test:
     - rst2html converts a simple reST input to HTML
     - docutils CLI --version works
"""
import os
import subprocess
import sys

failures = []
SP = os.environ.get("DOCUTILS_SITE_PACKAGES", "")
BIN = os.environ.get("DOCUTILS_BIN", "")

if not SP:
    print("FAIL: DOCUTILS_SITE_PACKAGES environment variable is not set or empty")
    sys.exit(1)

if SP not in sys.path:
    sys.path.insert(0, SP)

# Also add bin/ to PATH for CLI tests
if BIN:
    os.environ["PATH"] = BIN + os.pathsep + os.environ.get("PATH", "")

# 1. Package integrity check
init_file = os.path.join(SP, "docutils", "__init__.py")
if not os.path.isfile(init_file):
    failures.append("docutils/__init__.py missing")
else:
    # Read version from __init__.py without importing (avoids side effects)
    ns = {}
    with open(init_file) as f:
        for line in f:
            if line.startswith("__version__"):
                exec(line, ns)
                break
    ver = ns.get("__version__")
    if ver != "0.23":
        failures.append("version mismatch: expected 0.23, got " + repr(ver))
    else:
        print("OK: docutils.__version__ = 0.23")

core_file = os.path.join(SP, "docutils", "core.py")
if not os.path.isfile(core_file):
    failures.append("docutils/core.py missing")
else:
    print("OK: docutils/core.py present")

# 2. Functional test: import docutils and use its API
try:
    import docutils
    from docutils.core import publish_string
    # Convert a simple reST document to HTML
    rest_input = "Hello World\n==========\n\nThis is a test.\n"
    html_output = publish_string(rest_input, writer_name="html5")
    if isinstance(html_output, bytes):
        html_output = html_output.decode("utf-8")
    if "<h1>Hello World</h1>" in html_output or "Hello World" in html_output:
        print("OK: docutils publish_string HTML conversion works")
    else:
        failures.append("HTML conversion did not produce expected output")
except Exception as e:
    failures.append("functional API test error: " + str(e))

# 3. CLI smoke test: rst2html --version (if bin/ scripts available)
if BIN:
    rst2html = os.path.join(BIN, "rst2html")
    if os.path.isfile(rst2html):
        try:
            result = subprocess.run(
                [rst2html, "--version"],
                capture_output=True, text=True, timeout=10)
            output = (result.stdout + result.stderr).strip()
            if "0.23" in output:
                print("OK: rst2html --version = " + output)
            else:
                failures.append("rst2html --version unexpected output: " + output)
        except Exception as e:
            failures.append("rst2html CLI test error: " + str(e))
    else:
        failures.append("rst2html script not found in bin/")

# Result summary
if failures:
    print("FAIL:")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("ALL CHECKS PASSED")
