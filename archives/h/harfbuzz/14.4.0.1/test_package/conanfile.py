#!/usr/bin/env python3
"""Consumer test for HarfBuzz 14.4.0.1."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HarfbuzzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # libharfbuzz-icu 静态链接 icu4c（C++ 库），运行期需 libc++_shared.so，
        # 位于 OHOS 系统目录 /system/lib64（conanrun 只含 conan 包 lib 路径）。
        if self.settings.os == "OHOS":
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = "/system/lib64" + (
                ":" + existing if existing else ""
            )
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_harfbuzz")
        self.run(test_binary, env="conanrun")
