#!/usr/bin/env python3
"""Conan test_package — liblsl 1.18.0.b2 消费者测试（R28/R34）。

三条独立验证：
  1. C 消费者  ：find_package(LSL CONFIG) + LSL::lsl，走 C API 全链路
                （库标识 / streaminfo + XML 往返 / 本机回环 outlet→inlet 真实传样本）
  2. C++ 消费者：lsl_cpp.h 的 RAII 包装 + 模板 push/pull（证明安装出的 C++ 头文件
                能被 C++17 消费者直接包含并与 liblsl.so 正确链接）
  3. 裸环境 smoke：包内 bin/lslver 在 **不注入 conanrun 的 LD_LIBRARY_PATH** 的前提下
                直接执行成功 —— 这是唯一能证明「安装出的 RUNPATH 真的有效」的证据
                （conanrun 的 LD_LIBRARY_PATH 会掩盖错误的 RUNPATH）。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LiblslTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int) or 2
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j{}".format(jobs)])

    def test(self):
        self.run(os.path.join(self.cpp.build.bindir, "test_liblsl_c"), env="conanrun")
        self.run(os.path.join(self.cpp.build.bindir, "test_liblsl_cpp"), env="conanrun")

        # 裸环境 smoke：清掉 LD_LIBRARY_PATH，只靠包内 RUNPATH 找 ../lib/liblsl.so.2
        lslver = os.path.join(self.dependencies["liblsl"].package_folder,
                              "bin", "lslver")
        self.run('env -u LD_LIBRARY_PATH "{}" --version'.format(lslver))
