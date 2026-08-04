#!/usr/bin/env python3
"""Conan test_package for pcalc — 测试工具是否可用。

pcalc 是命令行工具，不是库。测试验证：
1. 源文件可编译（满足 L0c）
2. 可执行文件存在
3. 能正常运行并输出结果
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PcalcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # pcalc 是工具，测试可执行文件是否存在
        bindir = self.dependencies["pcalc"].cpp_info.bindirs[0]
        pcalc_bin = os.path.join(bindir, "pcalc")

        if not os.path.exists(pcalc_bin):
            # Windows 上可能有 .exe 后缀
            pcalc_bin = os.path.join(bindir, "pcalc.exe")

        self.output.info(f"Checking pcalc binary: {pcalc_bin}")
        assert os.path.exists(pcalc_bin), f"pcalc binary not found at {pcalc_bin}"

        # 运行简单计算测试
        self.output.info("Running pcalc test: 1+1")
        ret = self.run(f'"{pcalc_bin}" "1+1"', env="conanrun")
        assert ret == 0, f"pcalc exited with code {ret}"

        # 执行编译好的 test_pcalc 二进制，断言其退出码为 0
        self.output.info("Running compiled test_pcalc binary")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_pcalc")
        ret = self.run(test_bin, env="conanrun")
        assert ret == 0, f"test_pcalc exited with code {ret}"