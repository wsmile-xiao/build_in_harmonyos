#!/usr/bin/env python3
"""Conan test_package — NSPR 4.37

L1 test: verify NSPR headers are available and API functions link correctly.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class NsprTestConan(ConanFile):
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
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_nspr")
            # On OHOS musl, LD_LIBRARY_PATH set by env="conanrun" may not be
            # effective for binaries in non-standard paths (E186).
            # Explicitly set LD_LIBRARY_PATH to include the NSPR package's lib
            # directory, following the same pattern as airspyone-host.
            dep = self.dependencies["nspr"]
            lib_dir = os.path.join(str(dep.package_folder), "lib")
            ret = self.run(f'export LD_LIBRARY_PATH="{lib_dir}:$LD_LIBRARY_PATH"; {bin_path}', env="conanrun")
            if ret == 0:
                print(
                    'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
                    '"command":"test_nspr binary"}'
                )
            else:
                print(
                    'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,'
                    '"command":"test_nspr binary"}'
                )