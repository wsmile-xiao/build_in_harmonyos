#!/usr/bin/env python3
import os
import shutil

from conan import ConanFile


class FioTestConan(ConanFile):
    """test_package for fio executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
