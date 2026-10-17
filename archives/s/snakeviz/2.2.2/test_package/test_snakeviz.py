#!/usr/bin/env python3
"""Exercise the packaged snakeviz from a consumer's point of view.

Usage: test_snakeviz.py

snakeviz is a pure-Python wheel application whose web layer is tornado.  This
script verifies, with the Conan run environment applied (so ``snakeviz`` and
``tornado`` both resolve into their package payloads):

1. the wheel tree is importable and reports the exact version;
2. the real ``snakeviz -s`` HTTP server renders a cProfile file end to end —
   the profile is generated, the server started, a loopback request issued
   against the ``/snakeviz/<profile>`` route, and the HTML response checked.

The server is started via ``python3 -m snakeviz.cli`` — the documented
equivalent of the console script (the wheel's bin wrapper lives in the
environment bin dir, not in site-packages).
"""
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

import snakeviz


def main():
    assert snakeviz.VERSION == "2.2.2", snakeviz.VERSION

    # Real end-to-end server smoke: cProfile file rendered by `snakeviz -s`.
    import cProfile
    import glob

    prof_dir = tempfile.mkdtemp(prefix="svz-prof-")
    prof_path = os.path.join(prof_dir, "out.prof")
    cProfile.runctx("glob.glob('*')", {}, {"glob": glob}, prof_path)
    assert os.path.getsize(prof_path) > 0, "empty profile"

    port = 18923
    proc = subprocess.Popen(
        [sys.executable, "-m", "snakeviz.cli", "-s", "-H", "127.0.0.1",
         "-p", str(port), prof_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        body = None
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                url = ("http://127.0.0.1:" + str(port) + "/snakeviz/"
                       + urllib.parse.quote(prof_path))
                with urllib.request.urlopen(url, timeout=10) as resp:
                    body = resp.read()
                break
            except Exception:
                time.sleep(0.5)
        assert body is not None, "snakeviz server never responded"
        # The viz template embeds the Icicle/Sunburst viewer JS.
        assert b"snakeviz" in body.lower() or b"sunburst" in body.lower(), \
            body[:200]
        print("SNAKEVIZ-CONSUMER-OK")
    finally:
        proc.terminate()
        proc.wait()


main()
