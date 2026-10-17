#!/usr/bin/env python3
"""Conan consumer test - LLDB 17.0.0 debugger."""

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
        # 包内 bin/lldb 的 DT_NEEDED 是带路径前缀的 "lib/liblldb.so"，
        # 动态加载器将其作为相对于 cwd 的路径解析（不走 LD_LIBRARY_PATH），
        # 因此在包根目录下运行，使 lib/liblldb.so 命中包内库。
        # 1) Package binaries actually run.
        self.run(
            f'"{os.path.join(package_bin, "lldb")}" --version',
            cwd=package_folder,
            env="conanrun",
        )
        # 2) Consumer executable links against packaged liblldb and calls
        #    public SB API (SBDebugger::Create / SBTarget::CreateTarget /
    #    SBModule) — see test_consumer.cpp.
        executable = os.path.join(self.build_folder, "test_lldb_consumer")
        if not os.path.isfile(executable):
            raise ConanException(
                f"Consumer executable not found: {executable}")
        self.run(f'"{executable}" --self-check', cwd=package_folder, env="conanrun")