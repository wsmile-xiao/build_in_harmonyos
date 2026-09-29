#!/usr/bin/env python3
import os
import sys

from conan import ConanFile


class JoystickTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_joystick.py")
        self.run(
            f'"{sys.executable}" "{script}" "{bindir}"',
            env="conanrun",
        )
