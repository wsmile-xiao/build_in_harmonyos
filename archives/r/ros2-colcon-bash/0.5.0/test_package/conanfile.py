#!/usr/bin/env python3
"""Conan test_package for ros2-colcon-bash 0.5.0."""
import os
import sys

from conan import ConanFile


class Ros2ColconBashTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.recipe_folder, "test_ros2_colcon_bash.py")
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"', env="conanrun")
