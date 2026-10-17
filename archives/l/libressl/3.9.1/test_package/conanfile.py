#!/usr/bin/env python3
"""Consumer test for the packaged LibreSSL libraries."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibreSSLTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(
            self.cpp.build.bindirs[0],
            "test_libressl" + (".exe" if self.settings.os == "Windows" else ""),
        )
        if not os.path.isfile(executable):
            raise ConanException(
                f"LibreSSL consumer test executable is missing: {executable}"
            )
        if can_run(self):
            self.run(executable, env="conanrun")
        else:
            self.output.info(
                "Cross build: consumer test compiled and linked; runtime "
                "execution is deferred to the HarmonyOS PC emulator."
            )
