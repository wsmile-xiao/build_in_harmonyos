#!/usr/bin/env python3
"""Conan test_package — utf8.h consumer verification (R34).

utf8.h is a header-only library, so the consumer test compiles against the
installed <utf8.h> and asserts real API behaviour (length, codepoint decode,
concat/compare, validation, duplication). It fails to build when the package
artifacts are removed (CI L1e destructive negative test).
"""
import os

from conan import ConanFile


class Utf8HTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        inc = self.dependencies["utf8.h"].cpp_info.includedirs[0]
        self.run(f"{cc} -O2 -std=gnu99 -I{inc} test.c -o test_probe")

    def test(self):
        self.run("./test_probe", env="conanrun")
