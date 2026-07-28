#!/usr/bin/env python3
"""Conan test_package for LV2 1.18.11-git."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.layout import basic_layout


class Lv2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg_folder = dep.package_folder
        include_dir = os.path.join(pkg_folder, "include")
        source = os.path.join(self.source_folder, "test_lv2.c")
        binary = os.path.join(self.build_folder, "test_lv2")
        os.makedirs(self.build_folder, exist_ok=True)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            if cross_building(self):
                raise ConanInvalidConfiguration(
                    "Cross builds require tools.build:compiler_executables[c]"
                )
            cc = str(self.settings.compiler)
        self.run(f'"{cc}" -I"{include_dir}" "{source}" -o "{binary}"')
        if not os.path.exists(binary):
            raise AssertionError(f"LV2 consumer binary was not created: {binary}")

        required_files = [
            os.path.join(include_dir, "lv2", "core", "lv2.h"),
            os.path.join(pkg_folder, "lib", "lv2", "core.lv2", "manifest.ttl"),
            os.path.join(pkg_folder, "lib", "pkgconfig", "lv2.pc"),
        ]
        for path in required_files:
            if not os.path.exists(path):
                raise AssertionError(f"Missing packaged LV2 file: {path}")

        if can_run(self):
            self.run(f'"{binary}"')
