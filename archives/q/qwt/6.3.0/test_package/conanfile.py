#!/usr/bin/env python3
"""Conan test_package — 消费者视角验证 qwt 可链接且核心 API 可用。

qwt 依赖 qtbase，qtbase 的 conan 配方不导出 qtbase-config.cmake
（cmake_find_mode=none），因此这里不通过 find_package(qwt) 间接
触发 find_dependency(qtbase)，而是直接 find_package(Qt6) + 手动
链接 qwt 库，避免 CMake 配置失败。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QwtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qwt = self.dependencies["qwt"]
        qt = self.dependencies["qtbase"]
        tc.variables["QWT_INCLUDE_DIR"] = os.path.join(
            qwt.package_folder, "usr/local/qwt-6.3.0/include")
        tc.variables["QWT_LIBRARY_DIR"] = os.path.join(
            qwt.package_folder, "usr/local/qwt-6.3.0/lib")
        # qtbase 用 cmake_find_mode=none，手动指向 Qt6Config.cmake
        tc.variables["Qt6_DIR"] = os.path.join(
            qt.package_folder, "lib/cmake/Qt6")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            qwt = self.dependencies["qwt"]
            qt = self.dependencies["qtbase"]
            from conan.tools.env import Environment
            env = Environment()
            env.append_path("LD_LIBRARY_PATH", os.path.join(
                qwt.package_folder, "usr/local/qwt-6.3.0/lib"))
            env.append_path("LD_LIBRARY_PATH", os.path.join(
                qt.package_folder, "lib"))
            with env.vars(self).apply():
                self.run(os.path.join(self.cpp.build.bindir, "test_qwt"))
