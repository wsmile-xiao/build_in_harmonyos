#!/usr/bin/env python3
"""Conan test_package — opendkim 2.11.0-beta2 (L1 smoke test).

Builds test.c against the installed package (CMakeDeps + CMakeToolchain)
and runs it. test.c exercises the real libopendkim API surface
(dkim_init/dkim_libfeature/dkim_options/dkim_sign/dkim_header/dkim_eoh/
dkim_body/dkim_eom/dkim_getsighdr/dkim_free/dkim_close), so a broken
package fails at link time or at runtime (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpendkimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly so the exit code (non-zero on any
        # API check failure) propagates to conan create.
        binary = os.path.join(self.cpp.build.bindirs[0], "test_opendkim")
        self.run(f'"{binary}"', env="conanrun")
