#!/usr/bin/env python3
"""Conan test_package — libvpd 2.2.9 消费者视角验证（L1）。

CI 经 `conan create` 自动调用本包：编译并**实际执行**消费者用例
test_libvpd.c —— 该程序调用 libvpd 对外公开的 C API，验证库可被
上层应用正常编译、链接、调用跑通。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibvpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libvpd 的公开头文件 vpddbenv.h 直接 #include <sqlite3.h>，
        # 消费者需显式依赖 sqlite3 才能拿到该头文件的搜索路径
        self.requires("sqlite3/3.53.4")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 实际运行三个消费者用例二进制，其退出码即测试结果
        # （CI L0d 门禁要求 test() 必须实际执行、含 self.run()，不可为 stub）
        bindir = self.cpp.build.bindirs[0]
        # C 用例：覆盖全部 24 个公开 C API
        self.run(os.path.join(bindir, "test_libvpd_c"), env="conanrun")
        # C++ 用例：验证 libvpd_cxx.a 可被链接与调用
        self.run(os.path.join(bindir, "test_libvpd_cxx"), env="conanrun")
        # 鸿蒙专有用例：__OHOS__ 编译期定义 + 运行期平台身份 + libc++ 实证
        self.run(os.path.join(bindir, "test_libvpd_ohos"), env="conanrun")
