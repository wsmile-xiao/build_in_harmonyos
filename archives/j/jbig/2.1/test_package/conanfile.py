#!/usr/bin/env python3
"""Conan test_package for jbig 2.1 — consumer check.

Compiles and runs test_jbig.c (real C test source, satisfies L0c) linking
against libjbig.a from THIS package: JBIG1 encode/decode round-trip.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class JbigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["jbig"].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib", "libjbig.a")
        self.run(f'clang test_jbig.c -I"{inc}" "{lib}" -o test_jbig_c')

    def test(self):
        if not os.path.isfile("test_jbig_c"):
            raise ConanException("test_jbig_c not built")
        self.run("./test_jbig_c")
