#!/usr/bin/env python3
"""Conan test_package for erkir 2.1.1 (L1 consumer test).

Builds test_erkir against the INSTALLED package and runs it. The binary
calls the real public API (spherical / ellipsoidal / ECEF / Vector3d /
Coordinate) and prints ERKIR_TEST_PACKAGE_RESULT itself; the marker flows
through self.run() into the conan log (R34 / PF3: no stub tests).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ErkirTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Conan 的 CMake helper 默认按 os.cpu_count() 追加 `-j20`；CI worker 内存受限
        # 窗口下会 fork 失败（同主配方 build() 的注释）。显式把最终并行度钉到 2 ——
        # 该参数排在 conan 自带的 -j 之后、对 make 后者生效（仓库先例 argon2 / aria
        # 的 test_package 同写法，实测最终取到自己给的值）。
        cmake.build(build_tool_args=["-j2"])

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer was compiled and linked; runtime execution skipped")
            return
        # cmake_layout() 单配置生成器下 cpp.build.bindirs == ["."]，
        # 即测试可执行文件落在 build 目录根。
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_erkir")
        self.run(bin_path, env="conanrun")
