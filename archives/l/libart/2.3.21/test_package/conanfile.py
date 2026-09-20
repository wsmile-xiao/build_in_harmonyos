#!/usr/bin/env python3
"""Conan test_package — libart 2.3.21.

Consumer-perspective verification (L1): CMakeDeps consumes the final
package_folder produced by `conan create`, links against
libart::libart and exercises affine transforms, vpath->SVP
rasterization prep and the exported version constants.

test() executes both compiled consumer programs directly via
self.run(): test_libart (library API checks) and libart_ohos_test
(HarmonyOS AArch64 platform checks).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibArtTestConan(ConanFile):
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
        if not can_run(self):
            self.output.warning(
                "cross-building: cannot execute the consumer test binaries"
            )
            return

        bindir = self.cpp.build.bindirs[0]
        # Consumer test: version constants, affine math, vpath->SVP
        self.run(
            f'"{os.path.join(bindir, "test_libart")}"',
            cwd=self.build_folder,
            env="conanrun",
        )
        # HarmonyOS platform test: __OHOS__, AArch64, 64-bit pointers
        self.run(
            f'"{os.path.join(bindir, "libart_ohos_test")}"',
            cwd=self.build_folder,
            env="conanrun",
        )
