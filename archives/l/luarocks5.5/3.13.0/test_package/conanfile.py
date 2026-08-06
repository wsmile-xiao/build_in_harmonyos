#!/usr/bin/env python3
"""Conan test_package for luarocks5.5 3.13.0."""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class Luarocks55TestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = os.path.join("build", "generators")

    def test(self):
        dep = self.dependencies["luarocks5.5"]
        bin_dir = os.path.join(str(dep.package_folder), "bin")
        for command in ("luarocks", "luarocks-admin"):
            path = os.path.join(bin_dir, command)
            if not os.path.exists(path):
                raise ConanException(f"missing packaged command: {path}")

        if not can_run(self):
            self.output.info("cross-building: verified packaged commands; runtime execution is gated")
            return

        python = shutil.which("python3") or sys.executable
        test_script = os.path.join(self.source_folder, "test_luarocks55.py")
        luarocks = os.path.join(bin_dir, "luarocks")
        luarocks_admin = os.path.join(bin_dir, "luarocks-admin")
        self.run(
            f'"{python}" "{test_script}" "{luarocks}" "{luarocks_admin}"',
            env="conanrun",
        )
