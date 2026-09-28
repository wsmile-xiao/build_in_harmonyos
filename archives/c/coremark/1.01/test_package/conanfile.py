#!/usr/bin/env python3
"""Conan test_package for coremark 1.01 — consumer validation.

coremark is an application (CLI benchmark), not a library. The consumer
test runs the installed `coremark` binary through the standard validation
run via test.sh and asserts the self-check "Correct operation validated"
appears in the output (public CLI, public benchmark semantics).
"""
import os

from conan import ConanFile


class CoremarkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].package_folder
        exe = os.path.join(bindir, "bin", "coremark")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries. Use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"COREMARK_EXE='{exe}' {bash} test.sh", env="conanrun")