#!/usr/bin/env python3
"""htmldoc 1.9.21 test_package real test source (L0c: test source file).

Runs the installed htmldoc binary: --version assertion + real HTML→PDF
conversion smoke (writes a PDF, verifies output file + PDF header).
Usage: test_htmldoc.py <path-to-htmldoc-bin>
"""
import os
import subprocess
import sys
import tempfile

HTML = """<!DOCTYPE html>
<html><head><title>test</title></head>
<body><h1>htmldoc smoke</h1><p>hello world</p></body></html>
"""


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise AssertionError(f"command failed ({r.returncode}): {' '.join(cmd)}")
    return r


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_htmldoc.py <htmldoc-bin>")
    hbin = sys.argv[1]
    if not os.path.isfile(hbin):
        raise AssertionError(f"htmldoc binary missing: {hbin}")

    # 1) version assertion (binary runs on OHOS)
    r = run([hbin, "--version"])
    if "1.9.21" not in r.stdout and "1.9.21" not in r.stderr:
        raise AssertionError(f"unexpected version output: {r.stdout!r}")

    # 2) real HTML→PDF conversion smoke
    workdir = tempfile.mkdtemp(prefix="htmldoc-tp-")
    try:
        html = os.path.join(workdir, "t.html")
        pdf = os.path.join(workdir, "t.pdf")
        with open(html, "w") as f:
            f.write(HTML)
        run([hbin, "-f", pdf, html], cwd=workdir)
        if not os.path.isfile(pdf) or os.path.getsize(pdf) == 0:
            raise AssertionError(f"PDF output missing/empty: {pdf}")
        with open(pdf, "rb") as f:
            head = f.read(5)
        if head != b"%PDF-":
            raise AssertionError(f"output is not a PDF (header {head!r})")
        print(f"OK: htmldoc 1.9.21 --version + HTML→PDF conversion passed ({pdf})")
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
