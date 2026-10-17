#!/usr/bin/env python3
"""Conan consumer test for libpcre32 8.45 — pcre32_compile/exec roundtrip."""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["libpcre32"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_pcre32.c")
        self.run(
            f"{cc} -o test_pcre32 {src} "
            f"-I{pkg}/include -L{pkg}/lib -lpcre32 -lm",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_pcre32", env="conanrun")
