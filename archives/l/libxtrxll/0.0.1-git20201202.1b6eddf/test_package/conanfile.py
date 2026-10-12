#!/usr/bin/env python3
"""Conan test_package for libxtrxll — Conan L1 official test.

File location: archives/l/libxtrxll/0.0.1-git20201202.1b6eddf/test_package/conanfile.py

Compiles two consumer programs against the *installed* package and runs them:

  * test_consumer.c      — public API surface (discovery, open error mapping,
                           logging subsystem) using only device-independent,
                           deterministic behaviour.
  * test_ohos_offline.c  — HarmonyOS-specific properties of this adaptation:
                           static plugin registration and operation on a host
                           without the XTRX kernel driver / hardware.

Both programs link libxtrxll and call its public symbols, so the CI L1e
destructive reverse check (moving lib/ or include/ away) makes this test fail.
"""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

import os


class LibxtrxllTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else "."

        # Consumer integration test: public API surface.
        self.run(os.path.join(bindir, "test_consumer"), env="conanrun")

        # HarmonyOS-specific test: static plugin registration + no-hardware
        # operation on the target platform.
        self.run(os.path.join(bindir, "test_ohos_offline"), env="conanrun")
