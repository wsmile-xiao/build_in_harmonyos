#!/usr/bin/env python3
"""Conan test_package — buildcache 0.28.6

L1 smoke test: verifies that the buildcache binary is installed and can report
its version and copyright/help information. This is a consumer-perspective
test (R34) that genuinely depends on the installed binary.
"""
import os

from conan import ConanFile


class BuildcacheTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: actually execute the buildcache binary.
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
