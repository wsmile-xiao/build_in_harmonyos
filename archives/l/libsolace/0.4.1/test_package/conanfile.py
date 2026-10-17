#!/usr/bin/env python3
"""test_package for libsolace/0.4.1 — 消费者视角验证（L1，鸿蒙特有测试行）。

只通过**已安装包**（conan 生成的 libsolace::libsolace 导入目标 + 安装到 include/ 的头）
使用上游 API：不 include 上游源码树、不依赖 assert/NDEBUG——全部为显式计数检查，
任一失败进程非零退出（R34 反空壳：CI 会核查 test() 确实执行了真实二进制，拒绝仅回显的占位）。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibsolaceTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: consumer test is executed by the device-side verification"
            )
            return
        # cmake_layout 下可执行文件落在 build 目录根；self.cpp.build.bindir 可能解析为 "."
        # （readstat 先例：RUN "./test_x" → Error 127）。逐候选取首个真实存在的文件。
        name = "test_libsolace"
        candidates = [
            os.path.join(self.build_folder, name),
            os.path.join(os.path.abspath(self.cpp.build.bindir or "."), name),
            os.path.join(self.source_folder, name),
        ]
        binary = next((c for c in candidates if os.path.isfile(c)), candidates[0])
        self.output.info(f"consumer check: {binary}")
        self.run(f'"{binary}"', env="conanrun")
