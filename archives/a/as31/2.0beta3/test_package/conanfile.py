#!/usr/bin/env python3
"""Conan test_package for as31 2.0beta3.

R34: Test executes the as31 binary via popen and verifies
it prints usage output. The test binary is compiled with the
Conan-configured compiler (R33 compliant, no shell env vars).
"""
import os
import shutil

from conan import ConanFile


class As31TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(f'"{cc}" test.c -o test_as31')

    def test(self):
        # R34: Execute the test binary which calls as31
        bash = shutil.which("bash") or "bash"
        self.run(f'"{bash}" -c "./test_as31"', env="conanrun")
