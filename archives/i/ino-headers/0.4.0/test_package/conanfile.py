#!/usr/bin/env python3
"""Conan test_package — ino-headers 0.4.0 消费者测试。

R34 实质校验（上游无测试套件，本测试包为唯一测试载体）:
  1. test_ino.cpp（C++11 TU）: 覆盖全部公开 API——3 个 typedef 语义、
     6 个枚举值、26 个公开函数精确签名（decltype 编译期断言，不产生
     链接引用）、INO_BEGIN/END_C_DECLS 在 C++ 下可用 + 运行时枚举校验
  2. test_ino_c.c（C11 TU）: 头文件在纯 C 下可用（C API 本质检验）——
     typedef 语义 _Static_assert + 声明分隔宏 + 运行时枚举校验
  3. check_pkg.sh（打包布局与纯度）: 头文件布局 / pc 文件版本与
     ${pcfiledir} 可迁移性 / 头文件包纯度（无 bin、无编译产物）
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class InoHeadersTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
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
        dep = self.dependencies["ino-headers"]
        pkg = dep.package_folder
        if not os.path.isdir(pkg):
            raise Exception(f"ino-headers package folder not found: {pkg}")

        # 1) 布局/纯度脚本（真机 CONFIG_SHELL 提供 HMDFS bash，本地回退 bash）
        bash = os.environ.get("CONFIG_SHELL", "bash")
        script = os.path.join(self.source_folder, "check_pkg.sh")
        self.run(f'"{bash}" "{script}" "{pkg}"')

        # 2) CTest 双语言探针（交叉编译 OHOS 目标时推迟到目标端运行）
        if not can_run(self):
            self.output.info("Cross-built test_ino_cpp/test_ino_c; runtime "
                             "verification deferred to the OHOS target")
            return
        cmake = CMake(self)
        cmake.test()
