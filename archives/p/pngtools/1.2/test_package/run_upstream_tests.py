#!/usr/bin/env python3
"""Run the unmodified upstream pngtools unittest suite.

The upstream project uses testtools, fixtures, stestr and Pillow.  CI workers
for this repository only guarantee Python 3 and Conan, so this runner supplies
small standard-library shims and equivalent PNG test-data generation.  The
actual test modules and test methods are imported from the upstream source
archive without modification.
"""

import argparse
import os
import shutil
import subprocess
import sys
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--build-dir", required=True)
    args = parser.parse_args()

    source = os.path.abspath(args.source)
    build_dir = os.path.abspath(args.build_dir)

    sys.path.insert(0, os.path.join(HERE, "shim"))
    sys.path.insert(0, source)

    for tool in ("pnginfo", "pngchunks", "pngchunkdesc", "pngcp"):
        built = os.path.join(build_dir, tool)
        if not os.path.isfile(built):
            raise SystemExit("build did not produce %s" % built)
        shutil.copy2(built, os.path.join(source, tool))

    generator = os.path.join(HERE, "generate_test_images.py")
    testdata = os.path.join(source, "testdata")
    subprocess.run(
        [sys.executable, generator, "--output", testdata],
        check=True,
    )

    suite = unittest.defaultTestLoader.discover(
        os.path.join(source, "tests"),
        pattern="test_*.py",
        top_level_dir=source,
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(
        "UPSTREAM_TEST_RESULT total=%d failures=%d errors=%d skipped=%d"
        % (
            result.testsRun,
            len(result.failures),
            len(result.errors),
            len(result.skipped),
        )
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
