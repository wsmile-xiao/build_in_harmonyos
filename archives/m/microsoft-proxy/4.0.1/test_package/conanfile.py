#!/usr/bin/env python3
"""Conan test_package — microsoft-proxy 4.0.1 consumer smoke test.

Verifies that a downstream C++20 program can include <proxy/proxy.h>,
build a facade via pro::facade_builder and invoke through pro::proxy
(R34: test must exercise the packaged library API).
"""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class MsftProxy4TestConan(ConanFile):
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "example")
            self.run(bin_path, env="conanrun")
            # OHOS-specific test (see ohos_test.cpp): exercises the patched
            # trivial copy/relocate paths and the __cpp_lib_format guard.
            ohos_bin = os.path.join(self.cpp.build.bindir, "ohos_test")
            self.run(ohos_bin, env="conanrun")