#!/usr/bin/env python3
"""simde 0.8.4-rc3 consumer test.

编译并真实运行三个消费者程序（C / C++ / 原生别名层），全部调用 simde 公开 API：
  - test_simde      : C 模式 NEON + SSE2 + wasm + MSA 便携路径与平台能力断言
  - test_simde_cpp  : C++ 模式同类 API，覆盖上游 c/cpp 双语言注册面
  - test_native     : SIMDE_ENABLE_NATIVE_ALIASES 下的原生 NEON 别名一致性
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SimdeTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # L0d: 显式运行 CMake 构建的消费者可执行文件（真实执行，非空壳）
        bindir = self.cpp.build.bindirs[0]
        for exe in ("test_simde", "test_simde_cpp", "test_native"):
            self.run(os.path.join(bindir, exe), env="conanrun")
