#!/usr/bin/env python3
"""Conan test_package — fff consumer verification (R34).

fff is a header-only mocking framework, so the consumer test compiles against
the installed <fff.h> and asserts real API behaviour: call counting, argument
capture/history, global call history ordering, default return values, return
value sequences, custom fakes and RESET_FAKE. It fails to build when the
package artifacts are removed (CI L1e destructive negative test).
"""
import os

from conan import ConanFile


class FffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        inc = self.dependencies["fff"].cpp_info.includedirs[0]
        self.run(f"{cc} -O0 -std=c99 -I{inc} test.c -o test_probe")

    def test(self):
        self.run("./test_probe", env="conanrun")
