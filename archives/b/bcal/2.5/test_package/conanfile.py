#!/usr/bin/env python3
"""Conan test_package — bcal 2.5

Tests the bcal binary by running 'bcal -h' to verify version output
and 'bcal -c 255' to verify radix conversion functionality.
bcal is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class BcalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        # R33: derive bash path from Conan conf (compiler_executables),
        # not from os.environ.
        if self.settings.os == "OHOS":
            comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            cc = comp_execs.get("c", "")
            if cc:
                bash = os.path.join(os.path.dirname(cc), "bash")
            else:
                bash = "/data/service/hnp/bin/bash"
        else:
            bash = "bash"
        self.run(f"{bash} test.sh", env="conanrun")
