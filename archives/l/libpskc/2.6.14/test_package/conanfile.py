#!/usr/bin/env python3
"""Conan test_package for libpskc 2.6.14 — runs the R34 consumer check.

Compiles a C program against the packaged ``pskc/pskc.h`` + ``libpskc.so``,
drives the real PSKC parse/accessor/serialise pipeline, verifies the
``libpskc.pc`` pkg-config contract, and rejects malformed input.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        # libxml2 is needed at runtime by the packaged library.
        self.requires(self.tested_reference_str)
        self.requires("libxml2/2.15.3.1")

    def test(self):
        if not can_run(self):
            raise ConanException("cannot run on this platform")
        pkg = self.dependencies["libpskc"].package_folder
        if not os.path.isfile(os.path.join(pkg, "include", "pskc", "pskc.h")):
            raise ConanException(f"pskc/pskc.h missing under {pkg}/include")
        test_script = os.path.join(os.path.dirname(__file__), "test_libpskc.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_libpskc.py missing: {test_script}")

        # Point the consumer program at libxml2's runtime library dir.
        libxml2_pkg = self.dependencies["libxml2"].package_folder
        libxml2_lib = os.path.join(libxml2_pkg, "lib")
        self.run(f'{sys.executable} "{test_script}" "{pkg}" "{libxml2_lib}"',
                 env="conanrun")
