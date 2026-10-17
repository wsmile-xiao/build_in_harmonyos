#!/usr/bin/env python3
"""test_package for the pasco executable — runs the packaged `pasco` binary.

Consumer verification for an application package: nothing to link. The test drives the
installed executable against a synthetic Windows index.dat and asserts exit codes and
output shape (see test.sh).
"""
import os

from conan import ConanFile


class PascoTestConan(ConanFile):
    """test_package for pasco — executes the installed pasco binary via test.sh."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: use CONFIG_SHELL (mksh under /system/bin cannot exec ELF binaries).
        sh = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{sh} test.sh", env="conanrun")
