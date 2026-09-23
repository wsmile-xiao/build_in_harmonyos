#!/usr/bin/env python3
"""Conan test_package — calc 3.0.1.0

Tests the calc binary by running 'calc --version' to verify
executability and simple arithmetic expression.
calc is a CLI tool, so we test the binary directly.
"""
import os

from conan import ConanFile


class CalcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
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