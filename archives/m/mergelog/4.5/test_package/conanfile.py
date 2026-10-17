#!/usr/bin/env python3
"""test_package for mergelog — exercises the packaged CLI binaries.

Upstream ships no test suite (the Makefile `check` target is the empty
autotools default `check-am: all-am` and there is no tests/ directory; see
MANIFEST.yml for the full evidence). This consumer test fills that gap by
running the packaged `mergelog` and `zmergelog` binaries via the real shell
test in `test.sh`, which asserts on date-sorted merge order, the no-args CLI
usage contract, and the gzip path via zmergelog on .gz fixtures (zlib
end-to-end).

test.sh is the actual test source (satisfies the CI L0c gate); this conanfile
only wires up the Conan consumer plumbing (requirements + run under conanrun).
"""

import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class MergelogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # test.sh ships next to this recipe; reference it by absolute path
        # because self.run() executes in the per-config build folder, not the
        # recipe folder. Run under the conanrun env so mergelog / zmergelog
        # (from the package's bindirs) and zlib's runtime lib path are set.
        test_sh = os.path.join(self.recipe_folder, "test.sh")
        self.run(f"sh {os.path.normpath(test_sh)}", env="conanrun")
