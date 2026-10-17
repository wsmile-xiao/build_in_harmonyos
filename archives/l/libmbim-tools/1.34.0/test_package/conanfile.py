#!/usr/bin/env python3
"""test_package for libmbim-tools 1.34.0 — Conan L1 official test.

This package is an application (tools-only) package, so the test executes the
delivered command-line tools and asserts on their real output.  The OHOS
console shell (/system/bin/sh, mksh) cannot exec ELF binaries, so the smoke
test is driven through bash (CONFIG_SHELL) inside the conanrun environment
(which puts the package bin/ on PATH and the glib libs on LD_LIBRARY_PATH).
"""
import os

from conan import ConanFile


class LibmbimToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Bash wraps the tool invocations: OHOS /system/bin/sh (mksh) cannot
        # execute ELF binaries.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
