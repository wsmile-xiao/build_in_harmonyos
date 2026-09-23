#!/usr/bin/env python3
"""test_package for cwebx 3.52 — drives the installed ctanglex/cweavex for real.

R34: every check runs the packaged binaries and asserts on their output, and the
extracted C is compiled and executed, so a recipe that installs a non-working
binary cannot pass.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CwebxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            executables = self.conf.get("tools.build:compiler_executables",
                                        default={}, check_type=dict) or {}
            cc = executables.get("c", "clang")
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} test.sh "{cc}"', env="conanrun")
