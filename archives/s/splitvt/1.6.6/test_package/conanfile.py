#!/usr/bin/env python3
"""Consumer + OHOS-specific tests for splitvt 1.6.6.

Both suites execute the *installed* bin/splitvt under a real pseudo terminal
(they are the functional gate for the pseudo-terminal code path the recipe's
termios patch selects), so they fail closed if the package is removed:
conan's CI L1e destructive check has nothing to lean on otherwise.

Each suite prints one machine-readable summary line:
    RESULT: passed=N failed=M skipped=K
A nonzero exit code from either suite fails the test step.
"""

import os

from conan import ConanFile
from conan.errors import ConanException


class SplitvtTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = ("ptyharness.py", "test_splitvt_pty.py",
                     "test_ohos_specific.py")
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _binary(self):
        package_folder = self.dependencies["splitvt"].package_folder
        exe = os.path.join(package_folder, "bin", "splitvt")
        if not os.path.isfile(exe):
            raise ConanException("packaged executable missing: %s" % exe)
        return exe

    def test(self):
        binary = self._binary()
        # python3 is on PATH on the HarmonyOS PC (hnp toolchain); allow the
        # harness to pin an explicit interpreter.
        python = os.environ.get("CONAN_TEST_PYTHON3") or "python3"
        # The suites import ptyharness.py from their own directory, which
        # conan exports alongside them; run them from there.
        for suite in ("test_splitvt_pty.py", "test_ohos_specific.py"):
            script = os.path.join(self.source_folder, suite)
            self.run('"%s" "%s" "%s"' % (python, script, binary),
                     env="conanrun")
