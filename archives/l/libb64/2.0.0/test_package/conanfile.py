#!/usr/bin/env python3
"""Conan test_package for libb64 2.0.0 — real functional Base64 encode/decode test.

Compiles a C program that links against libb64 and:
  1. Encodes a fixed plaintext string with the real libb64 2.0.0 C API.
  2. Verifies the encoded output equals the expected Base64 string.
  3. Decodes the Base64 string back (both one-shot and multi-call streaming).
  4. Verifies the decoded output equals the original plaintext.

This is NOT an include-only test: it links and runs the library.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy


class Libb64TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Copy the C test source into the build folder so it is self-contained.
        # Under `conan test` the build folder may equal the source folder, in
        # which case the file is already present and copy() would refuse it.
        if os.path.normpath(self.source_folder) != os.path.normpath(self.build_folder):
            copy(self, "test_b64.c", self.source_folder, self.build_folder)

    def build(self):
        # R33: read the OpenHarmony toolchain from Conan conf, never from shell env.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        dep = self.dependencies["libb64"]
        include_dir = os.path.join(dep.package_folder, "include")
        lib_dir = os.path.join(dep.package_folder, "lib")
        self.run(
            f'"{cc}" -O2 -I"{include_dir}" -L"{lib_dir}" '
            f'"{os.path.join(self.build_folder, "test_b64.c")}" -o '
            f'"{os.path.join(self.build_folder, "test_b64")}" -lb64',
            env="conanbuild",
        )

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_b64"), env="conanrun")
