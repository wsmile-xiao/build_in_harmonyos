#!/usr/bin/env python3
"""Conan test_package for libextractor 1.13（L1 消费者测试）。

从使用者视角编译、链接并调用 libextractor 的公开 API 提取元数据，
断言由提取结果决定退出码。插件目录由包自身的 runenv_info 注入
（LIBEXTRACTOR_PREFIX），依赖 .so 由 conanrun 的 LD_LIBRARY_PATH 提供
（musl 忽略 DT_RUNPATH，必须走 LD_LIBRARY_PATH）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibextractorTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libextractor")
        self.output.info("LIBEXTRACTOR_PREFIX={}".format(
            os.environ.get("LIBEXTRACTOR_PREFIX", "<unset in build env>")))
        self.run('"{}"'.format(exe), env="conanrun")
