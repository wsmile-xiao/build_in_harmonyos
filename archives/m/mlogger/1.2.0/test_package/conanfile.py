#!/usr/bin/env python3
"""Consumer test for the mlogger CLI package.

Runs test.sh which invokes the packaged `mlogger` binary across version, help,
stderr echo, priority, argv-join, and file-source paths with deterministic
string assertions on captured output. test.sh exits non-zero on any assertion
failure, so self.run() raises and fails the Conan test (no "did not crash"
gating).
"""

import os
import shutil

from conan import ConanFile


class MloggerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def _select_shell(self):
        # OHOS /system/bin/sh (mksh) may not exec ELF binaries directly on some
        # devices; prefer bash when available. Resolve via PATH / CONFIG_SHELL
        # so no machine-specific path is hardcoded (R33-equivalent for shells).
        shell = os.environ.get("CONFIG_SHELL")
        if shell and shutil.which(shell):
            return shell
        for candidate in ("bash", "sh"):
            found = shutil.which(candidate)
            if found:
                return found
        return "sh"

    def test(self):
        shell = self._select_shell()
        # tool_requires puts the mlogger binary on PATH in the conanbuild env
        # (mlogger is an application, not a runtime library). Deterministic
        # gate: test.sh asserts exact stdout / captured substrings and exits 1
        # if any fail; self.run() raises on non-zero.
        self.run(f"{shell} test.sh", env="conanbuild")
