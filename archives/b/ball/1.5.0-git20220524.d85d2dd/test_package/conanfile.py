#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/ball/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BallTestConan(ConanFile):
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
        # E298: 上游 CMakeLists 强制 BUILD_SHARED_LIBS=TRUE（产物为 libBALL.so），
        # conanrun 环境只含依赖库（qt5/boost）的 lib 路径，不含 ball 包自身 lib 目录，
        # 消费者进程运行时找不到 libBALL.so（Error loading shared library libBALL.so.1.5）。
        # 显式把 ball 包 lib 目录加入 LD_LIBRARY_PATH 后运行消费者二进制。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ball")
        ball_lib = os.path.join(self.dependencies["ball"].package_folder, "lib")
        self.run(
            f"export LD_LIBRARY_PATH={ball_lib}:$LD_LIBRARY_PATH && {test_bin}",
            env="conanrun",
        )
