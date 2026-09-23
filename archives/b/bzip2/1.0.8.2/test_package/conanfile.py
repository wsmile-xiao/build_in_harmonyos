#!/usr/bin/env python3
"""Conan test_package — bzip2 1.0.8.2 smoke test.

Verifies package-provided binaries and library API:
- bzip2 --version (binary smoke test)
- BZ2_bzlibVersion() + compress/decompress round-trip (API test)
"""
import os

from conan import ConanFile


class Bzip2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        pkg = self.dependencies["bzip2"].package_folder
        src = os.path.join(self.source_folder, "test_bzip2.c")
        self.run(
            f"{cc} -o test_bzip2 {src} "
            f"-I{os.path.join(pkg, 'include')} "
            f"-L{os.path.join(pkg, 'lib')} -lbz2 -static",
            env="conanbuild",
        )

    def test(self):
        self.run("bzip2 --version", env="conanrun")
        self.run("./test_bzip2", env="conanrun")
