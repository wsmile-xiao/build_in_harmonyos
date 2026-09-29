#!/usr/bin/env python3
"""Conan test_package — observable_unique_ptr 0.7.3 消费者测试（header-only 交付形态）。

消费者面真实使用 oup:: 公共 API（来自 conan 包 include/ 交付件）：
- 交付面断言：包内头文件存在且含上游卫士与核心类（3 条）；
- 运行期断言 25 条：sealed/unique 两种所有权、observer 拷贝移动、reset/release 过期语义、
  enable_observer_from_this；逐条打印 `[consumer] PASS`，末行 `[consumer] TOTAL=25 FAIL=0`；
- 断言用显式检查而非 assert()（Release 下 NDEBUG 会把 assert 编译掉 → 假绿）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ObservableUniquePtrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 把交付进包的 include/ 绝对路径传给 CMake，测试程序据此对交付头做内容断言
        pkg_folder = self.dependencies["observable_unique_ptr"].package_folder
        cmake = CMake(self)
        cmake.configure(
            variables={
                "OUP_PKG_INCLUDE_DIR": os.path.join(pkg_folder, "include"),
            }
        )
        cmake.build()

    def test(self):
        # L0d/PF3 门禁：必须真实执行被测二进制（拒绝空壳形态的测试方法）
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found in test_package layout")
        bin_path = os.path.join(bindirs[0], "test_observable_unique_ptr")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")
