#!/usr/bin/env python3
"""Conan test_package — nanoflann 1.12.1 (header-only KD-tree / KNN lib).

Consumer-side verification: compiles against the packaged header and performs
a kNN nearest-neighbor search (R34: substantive dependency on the tested
package's API).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class NanoflannTestConan(ConanFile):
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
        if cross_building(self) or str(self.settings.os) == "OHOS":
            # OHOS ELF cannot run in the local noexec sandbox; CI runs it on the target worker.
            self.output.info("OHOS/noexec environment: skip runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_nanoflann"), env="conanrun")