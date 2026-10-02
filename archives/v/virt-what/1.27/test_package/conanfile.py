#!/usr/bin/env python3
"""Conan consumer tests for the packaged virt-what tools."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class VirtWhatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("virt-what consumer tests need a runnable host")

        package = self.dependencies["virt-what"].package_folder
        bindir = os.path.join(package, "bin")
        test_dir = os.path.dirname(__file__)

        self.run(
            f'{sys.executable} "{os.path.join(test_dir, "test_virt_what.py")}" '
            f'"{bindir}"',
            env="conanrun",
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f'{sys.executable} "{os.path.join(test_dir, "test_ohos.py")}" '
                f'"{bindir}"',
                env="conanrun",
            )
