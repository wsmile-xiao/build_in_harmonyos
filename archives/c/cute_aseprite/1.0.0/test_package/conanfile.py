#!/usr/bin/env python3
"""Conan test_package for cute_aseprite 1.0.0 — exercises the real public API.

Builds test_aseprite.c with the system C compiler against the packaged
cute_aseprite.h, then runs the binary. The test parses an in-memory minimal
.ase file through cute_aseprite_load_from_memory() and asserts the parsed
frame/layer/cel/pixel fields, then frees. Emits HMBS_TEST_PACKAGE_RESULT.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class CuteAsepriteTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Compile the test TU with CUTE_ASEPRITE_IMPLEMENTATION using the
        # same compiler from the active profile (clang on OHOS). Include dir
        # comes straight from the packaged dependency.
        dep = self.dependencies["cute_aseprite"]
        include = os.path.join(dep.package_folder, "include")
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_aseprite.c")
        exe = os.path.join(self.build_folder, "test_aseprite")
        self.run(f"{cc} -std=c99 -O2 -I{include} -o {exe} {src} -DCUTE_ASEPRITE_IMPLEMENTATION",
                 cwd=self.build_folder)

    def test(self):
        if cross_building(self):
            self.output.info("Cross-compiling: test binary built but not run on host")
            return
        exe = os.path.join(self.build_folder, "test_aseprite")
        self.run(exe)