#!/usr/bin/env python3
"""Conan test_package — rc_ptr 0.0.2 消费者测试（header-only 交付形态）。

消费者面真实使用 memory:: 公共 API（来自 conan 包 include/ 交付件）：
- 交付面断言：包内头文件 rc_ptr/rc_ptr.hpp 存在且含上游核心类（2 条）；
- 运行期断言 16 条：make_rc/copy/move/reset/swap 引用计数语义、weak_rc_ptr 的
  lock/expired/赋值抛错、enable_rc_from_this、自定义 deleter 只调用一次、
  owner_less 严格序、bool/`*`/`->` 运算、数组下标、unique()；逐条打印
  `[consumer] PASS`，末行 `[consumer] TOTAL=18 FAIL=0`；
- 另含 3 条 static_assert 编译期约束（element_type/数组退化/异常类型）。
- 断言用显式检查而非 assert()（Release 下 NDEBUG 会把 assert 编译掉 → 假绿）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class RcPtrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 把交付进包的 include/ 绝对路径传给 CMake，测试程序据此对交付头做内容断言
        pkg_folder = self.dependencies["rc_ptr"].package_folder
        cmake = CMake(self)
        cmake.configure(
            variables={
                "RC_PTR_PKG_INCLUDE_DIR": os.path.join(pkg_folder, "include"),
            }
        )
        cmake.build()

    def test(self):
        # L0d/PF3 门禁：必须真实执行被测二进制（拒绝空壳形态的测试方法）
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("No bindirs found in test_package layout")
        bin_path = os.path.join(bindirs[0], "test_rc_ptr")
        if not os.path.isfile(bin_path):
            raise ConanException(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")
