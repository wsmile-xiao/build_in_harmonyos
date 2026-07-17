#!/usr/bin/env python3
"""Conan test_package — showkey 1.10 binary verification.

showkey is an interactive TTY tool with no library API and no --version/--help
flags. With no tty on stdin it deterministically reports "stdin is not a tty"
and exits non-zero; the test asserts that behavior to prove the installed
binary is genuine and runnable.
"""
import os

from conan import ConanFile


class ShowkeyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["showkey"]
        showkey_bin = os.path.join(dep.package_folder, "bin", "showkey")
        # OHOS /system/bin/sh (mksh) cannot launch ELF binaries — use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh "{showkey_bin}"', env="conanrun")
