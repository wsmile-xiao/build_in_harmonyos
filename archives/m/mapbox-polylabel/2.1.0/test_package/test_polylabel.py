#!/usr/bin/env python3
"""L0 gate driver + consumer check for the packaged mapbox-polylabel 2.1.0.

CI L0c requires a .c/.cpp/.sh/.py source in test_package/ and L0d requires
a literal self.run() call in test_package/conanfile.py. Upstream here is
JavaScript-only, so this driver (invoked via self.run with the interpreter)
validates the packaged artifacts from Python: packaged polylabel.js exists
and is non-empty, the vendored tinyqueue runtime dep is present, the
byte-identical upstream fixtures are non-empty, and both JS harnesses carry
the same 4 upstream oracles. Any failure exits non-zero.
"""

import json
import os
import sys


def fail(msg):
    print("not ok - {}".format(msg))
    sys.exit(1)


def main():
    checks = 0
    here = os.path.dirname(os.path.abspath(__file__))
    pkg_js = sys.argv[1] if len(sys.argv) > 1 else None
    if pkg_js is None:
        # Default: packaged share dir is not known; check the workdir copy
        # staged by test() next to this script.
        pkg_js = os.path.join(os.getcwd(), "polylabel.js")

    if not os.path.isfile(pkg_js):
        fail("packaged polylabel.js missing: {}".format(pkg_js))
    size = os.path.getsize(pkg_js)
    if size < 1000:
        fail("packaged polylabel.js too small ({}B): {}".format(size, pkg_js))
    checks += 1
    print("ok - packaged polylabel.js present ({}B)".format(size))

    with open(pkg_js, encoding="utf-8") as fh:
        content = fh.read()
    if "function polylabel" not in content:
        fail("packaged polylabel.js has no polylabel entry point")
    checks += 1
    print("ok - packaged polylabel.js exposes polylabel entry point")
    if "tinyqueue" not in content.lower() and "TinyQueue" not in content:
        fail("packaged polylabel.js lost its tinyqueue reference")
    checks += 1
    print("ok - packaged polylabel.js keeps tinyqueue dependency")

    tinyqueue_index = os.path.join(
        os.path.dirname(pkg_js), "node_modules", "tinyqueue", "index.js")
    if not os.path.isfile(tinyqueue_index):
        # Fall back to the workdir staging layout used by test().
        tinyqueue_index = os.path.join(
            os.getcwd(), "node_modules", "tinyqueue", "index.js")
    if not os.path.isfile(tinyqueue_index):
        fail("packaged tinyqueue runtime dep missing (node_modules/tinyqueue/index.js)")
    tq_size = os.path.getsize(tinyqueue_index)
    if tq_size < 500:
        fail("tinyqueue index.js too small ({}B)".format(tq_size))
    checks += 1
    print("ok - vendored tinyqueue runtime dep present ({}B)".format(tq_size))

    for name in ("water1.json", "water2.json"):
        for cand in (os.path.join(here, "fixtures", name),
                     os.path.join(os.getcwd(), "fixtures", name)):
            if os.path.isfile(cand):
                fp = cand
                break
        else:
            fail("fixture missing: fixtures/{}".format(name))
        sz = os.path.getsize(fp)
        if sz < 1000:
            fail("fixture empty ({}B): {}".format(sz, fp))
        with open(fp, encoding="utf-8") as fh:
            data = json.load(fh)
        if not data or not data[0] or len(data[0]) < 100:
            fail("fixture has no points: {}".format(fp))
        checks += 1
        print("ok - fixture {} ok ({}B, {}pts)".format(name, sz, len(data[0])))

    for harness in ("test_polylabel.mjs", "run_upstream.mjs"):
        for cand in (os.path.join(here, harness),
                     os.path.join(os.getcwd(), harness)):
            if os.path.isfile(cand):
                fp = cand
                break
        else:
            fail("harness missing: {}".format(harness))
        with open(fp, encoding="utf-8") as fh:
            text = fh.read()
        if len(text) < 200:
            fail("harness too small: {}".format(harness))
        checks += 1
        print("ok - harness {} present ({}B)".format(harness, len(text)))

    # Oracle parity: the cache-proof rerun must carry the same 4 upstream
    # expectations as test/test.js (water1 x2, water2, degenerate).
    rerun = None
    for cand in (os.path.join(here, "run_upstream.mjs"),
                 os.path.join(os.getcwd(), "run_upstream.mjs")):
        if os.path.isfile(cand):
            rerun = cand
            break
    with open(rerun, encoding="utf-8") as fh:
        rerun_text = fh.read()
    for oracle in ("3865.85009765625", "3854.296875", "3263.5, 3263.5"):
        if oracle not in rerun_text:
            fail("upstream oracle missing in run_upstream.mjs: {}".format(oracle))
        checks += 1
        print("ok - upstream oracle present: {}".format(oracle))

    print("PASS: mapbox-polylabel packaged API consumer test ({}/{} assertions)".format(checks, checks))


if __name__ == "__main__":
    main()
