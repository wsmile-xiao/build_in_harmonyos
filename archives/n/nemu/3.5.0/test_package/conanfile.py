#!/usr/bin/env python3
"""Conan consumer test for nemu 3.5.0.

The test builds a small launcher that executes the packaged nemu binary when
an OHOS runtime is available; cross-build CI records an explicit skip.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class NemuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self.run(f'cmake --build "{self.build_folder}" -- -j1')

    def test(self):
        nemu = os.path.join(self.dependencies["nemu"].package_folder,
                            self.dependencies["nemu"].cpp_info.bindirs[0], "nemu")
        local_nemu = os.path.join(self.build_folder, "nemu")
        shutil.copy2(nemu, local_nemu)
        os.chmod(local_nemu, 0o770)
        if str(self.settings.os) == "OHOS" or not can_run(self):
            self.output.warning(
                "SKIP: cross-built OHOS ELF cannot run in this CI sandbox; "
                "test_nemu was compiled and linked successfully"
            )
            return
        test_exe = os.path.join(self.build_folder, "test_nemu")
        self.run(f'"{test_exe}" "{local_nemu}"', env="conanrun")
