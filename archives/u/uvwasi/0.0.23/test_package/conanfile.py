#!/usr/bin/env python3
"""Conan test_package — uvwasi 0.0.23

R34: 实质依赖被测包 API（uvwasi_options_init / uvwasi_init / uvwasi_destroy /
uvwasi_embedder_err_code_to_string），并经 libuv 创建内部事件循环。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class UvwasiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # uvwasi.h 公开 include 了 libuv 的 uv.h，测试直接消费 uv.h，
        # 故显式直接依赖 libuv，让 CMakeDeps 生成其完整（含 include 目录）配置。
        self.requires("libuv/1.52.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 直接运行测试二进制：经 conanrun 注入运行期环境（libuv.so 路径），
        # 取进程退出码；不另跑 ctest，避免对同一 test_uvwasi 重复执行。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_uvwasi"), env="conanrun")
