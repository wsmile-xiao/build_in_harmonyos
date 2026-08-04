#!/usr/bin/env python3
"""Conan test package for linux-headers-5.15/5.15.211."""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LinuxHeadersTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dependency = self.dependencies[self.tested_reference_str]
        pkg = dependency.package_folder
        script = os.path.join(self.source_folder, "test_linux_headers.py")
        recipe_folder = dependency.recipe_folder
        self.run(
            f'"{sys.executable}" "{script}" "{pkg}" "{recipe_folder}"',
            env="conanrun",
        )

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = (
            compilers.get("c")
            or os.environ.get("CC")
            or shutil.which("clang")
            or shutil.which("cc")
            or "cc"
        )
        source = os.path.join(self.source_folder, "test_linux_headers.c")
        binary = os.path.join(self.build_folder, "test_linux_headers")
        include_dir = os.path.join(pkg, "include")
        os.makedirs(self.build_folder, exist_ok=True)
        self.run(f'"{cc}" -I"{include_dir}" "{source}" -o "{binary}"')
        if can_run(self):
            self.run(f'"{binary}"', env="conanrun")
