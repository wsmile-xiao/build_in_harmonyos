#!/usr/bin/env python3
"""Consumer test for the v7 C API."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class V7TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        dependency = self.dependencies["v7"]
        include_dir = os.path.join(dependency.package_folder, "include")
        library_dir = os.path.join(dependency.package_folder, "lib")
        source = os.path.join(self.source_folder, "test_v7.c")
        binary = os.path.join(self.build_folder, "test_v7")
        self.run(
            f'"{cc}" "{source}" -I"{include_dir}" -L"{library_dir}" '
            f"-lv7 -lm -o \"{binary}\""
        )

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_v7"), env="conanrun")
        else:
            self.output.warning("Cross-compiled consumer binary was not runnable")
