#!/usr/bin/env python3
"""Conan test_package for cute_png 1.0.0 — exercises the real public API.

Builds test_cute_png.c with the system C compiler against the packaged
cute_png.h, then runs the binary. The test defines TINYDEFLATE_IMPL
(the 1.0.0 version carrier's implementation macro) and exercises the
tdLoadPNG / tdLoadPNGMem PNG decode path with a tiny valid PNG, asserting
the decoded pixel value. Emits HMBS_TEST_PACKAGE_RESULT.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class CutePngTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Compile the test TU with TINYDEFLATE_IMPL using the same
        # compiler from the active profile (clang on OHOS). Include dir comes
        # straight from the packaged dependency.
        dep = self.dependencies["cute_png"]
        include = os.path.join(dep.package_folder, "include")
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_cute_png.c")
        exe = os.path.join(self.build_folder, "test_cute_png")
        self.run(f"{cc} -std=c99 -O2 -I{include} -o {exe} {src}",
                 cwd=self.build_folder)

    def test(self):
        if cross_building(self):
            self.output.info("Cross-compiling: test binary built but not run on host")
            return
        exe = os.path.join(self.build_folder, "test_cute_png")
        self.run(exe)
