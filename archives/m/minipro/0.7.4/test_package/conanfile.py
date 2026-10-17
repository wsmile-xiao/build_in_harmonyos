#!/usr/bin/env python3
"""Conan test_package for minipro — runs test.sh which invokes the minipro binary.

minipro is a command-line tool, not a library. Test by running the binary
(--version smoke test + --help to verify core function).
test.sh is the source file for CI L0c compliance.
"""
import os

from conan import ConanFile


class MiniproTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
