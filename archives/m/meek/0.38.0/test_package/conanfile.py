#!/usr/bin/env python3
"""Conan test_package — meek 0.38.0.

Verifies that meek-client and meek-server binaries are functional by running
them without the required TOR_PT_MANAGED_TRANSPORT_VER environment variable
and checking for the expected ENV-ERROR output (R34: real binary invocation).

File location: archives/m/meek/0.38.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class MeekTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Skip on cross-compilation: target arch binaries cannot run on
        # x86_64 CI workers.
        if cross_building(self):
            self.output.info("Cross-compiling: skipping binary execution test")
            return
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
