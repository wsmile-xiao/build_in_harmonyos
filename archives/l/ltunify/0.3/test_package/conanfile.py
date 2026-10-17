#!/usr/bin/env python3
"""test_package conanfile - ltunify 0.3 (application package)."""
import os

from conan import ConanFile


class LtunifyTestConan(ConanFile):
    """Runs test.sh, which exercises both shipped binaries."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
