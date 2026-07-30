#!/usr/bin/env python3
"""Conan test_package - screenresolution 1.6."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ScreenresolutionTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["screenresolution"]
        screenresolution = os.path.join(dep.package_folder, "bin", "screenresolution")
        if self.settings.os == "OHOS":
            self.run(f'sh test.sh "{screenresolution}"', env="conanrun")
        else:
            self.run(f'"{screenresolution}" -version', env="conanrun")
