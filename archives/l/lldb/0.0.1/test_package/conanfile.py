#!/usr/bin/env python3
"""Conan consumer test - LLDB 0.0.1 debugger (standalone build).

实质依赖（R34）：消费者链接包内 liblldb 并驱动公开 SB API
（SBDebugger/SBTarget/SBModule/SBBreakpoint/SBSection）；
包内二进制本体亦实际执行（--version）。全部用例无 ptrace、
不派生进程（CI 安全）。
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class LldbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        package_folder = self.dependencies["lldb"].package_folder
        tc = CMakeToolchain(self)
        tc.cache_variables["LLDB_INCLUDE_DIR"] = os.path.join(
            package_folder, "include")
        tc.cache_variables["LLDB_LIB_DIR"] = os.path.join(
            package_folder, "lib")
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            return
        package_folder = self.dependencies["lldb"].package_folder
        package_bin = os.path.join(package_folder, "bin")
        # 1) Package binaries actually run.
        self.run(
            f'"{os.path.join(package_bin, "lldb")}" --version',
            cwd=package_folder,
            env="conanrun",
        )
        # 2) Consumer executable links against packaged liblldb and calls
        #    public SB API — C1 debugger 实例化/版本, C2 target 创建 +
        #    模块符号, C3 断点/section 尺寸（见 test_consumer.cpp）。
        executable = os.path.join(self.build_folder, "test_lldb_consumer")
        if not os.path.isfile(executable):
            raise ConanException(
                f"Consumer executable not found: {executable}")
        self.run(f'"{executable}" --self-check', cwd=package_folder,
                 env="conanrun")
