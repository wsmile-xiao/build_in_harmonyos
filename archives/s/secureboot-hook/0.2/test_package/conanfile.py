#!/usr/bin/env python3
"""Conan test_package for secureboot-hook 0.2 — Shell script test.

Verifies that the installed hook script and config file exist and are correct.
The hook script cannot be fully executed (requires Void Linux + dracut + sbctl),
but we verify file presence, permissions, and content via test.sh.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class SecurebootHookTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["secureboot-hook"]
            etc_kernel = os.path.join(dep.package_folder, "etc", "kernel.d")

            bash_path = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or shutil.which("bash")
                or "/usr/local/bin/bash"
            )

            self.run(
                f'cd "{self.source_folder}" && '
                f'"{bash_path}" test.sh "{etc_kernel}"',
                env="conanrun"
            )
