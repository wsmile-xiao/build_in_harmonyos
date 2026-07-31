#!/usr/bin/env python3
"""Consumer test for remrun."""

import os

from conan import ConanFile


class RemrunTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def _remrun(self):
        dep = self.dependencies["remrun"]
        return os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "remrun")

    def test(self):
        if self.conf.get("tools.build:skip_test", default=False):
            return
        if self.settings.os == "Windows":
            return
        shell = os.environ.get("CONFIG_SHELL", "sh")
        script = os.path.join(self.source_folder, "test_remrun.sh")
        self.run(f'"{shell}" "{script}" "{self._remrun()}"', env="conanrun")
