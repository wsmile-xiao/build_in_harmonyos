#!/usr/bin/env python3
# test_package/conanfile.py — mstch 1.0.2 consumer test
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The test binary must actually execute. On OHOS the default shell
        # (/system/bin/sh, mksh) cannot exec ELF binaries, so wrap the
        # invocation with bash when available (same approach as the
        # rapidjson recipe).
        if not can_run(self):
            self.output.warning("Cross-building: skipping run of test_package")
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f'{bash} -c "{bin_path}"', env="conanrun")
