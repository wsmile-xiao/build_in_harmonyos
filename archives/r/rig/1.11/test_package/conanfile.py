#!/usr/bin/env python3
"""Conan test_package for rig 1.11."""
import os
import shutil

from conan import ConanFile


class RigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_rig.sh")
        self.run(f"{shell} {script} ./bin/rig ./share/rig", env="conanrun", cwd=pkg_folder)
