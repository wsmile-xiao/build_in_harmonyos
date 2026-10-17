#!/usr/bin/env python3
"""test_package —— libkysdk-base 消费者测试（Conan L1 / R34）。

真实调用被测包安装后的公开 API（非空壳测试）：
  kydatastruct : kysdk_create_skiplist / kysdk_skiplist_insert /
                 kysdk_skiplist_search / kysdk_skiplist_delete /
                 kysdk_destroy_skiplist
  kyutils      : kdkVolumeBaseNumericalConvert
断言失败时进程返回非零，conan create 的 test() 即失败。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibkysdkBaseTestConan(ConanFile):
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
        # 包内 .so 带 SONAME，运行时按 SONAME 查找；必须注入 conanrun 环境
        # （LD_LIBRARY_PATH 含包内 lib 目录），与 libayatana-common 同法。
        bindirs = self.cpp.build.bindirs
        self.run(os.path.join(bindirs[0], "test_libkysdk-base"), env="conanrun")
