#!/usr/bin/env python3
"""test_package for the trimal package — consumer tests for the CLI binaries.

Runs test.sh in the conanrun environment (PATH contains the installed bin/),
where the tests invoke the installed trimal/readal/statal binaries the same way
an end user would.
"""
import os
import shutil

from conan import ConanFile


class TrimalTestConan(ConanFile):
    """Consumer test: executes the installed trimal/readal/statal binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
