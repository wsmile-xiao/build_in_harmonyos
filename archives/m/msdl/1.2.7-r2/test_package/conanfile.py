#!/usr/bin/env python3
"""Conan test_package — msdl 1.2.7-r2 (L1 + HarmonyOS 专项测试).

test_msdl.c 覆盖三项:
1. L1 基础: 无参运行打印 usage、退出码 1（可执行、动态链接正常）。
2. HarmonyOS 专项: 进程内 ELF 解析 —— ELF64/AArch64/musl 解释器
   /lib/ld-musl-aarch64.so.1、DT_NEEDED 仅 libc.so（目标环境正确性）。
3. HarmonyOS 专项: 进程内极简 HTTP 服务器 + msdl 真实下载 64 KiB
   文件并逐字节比对（socket/GET/响应解析/写盘全链路，覆盖 msdl
   先探测 mmsh 再 fallback http 的真实网络行为）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MsdlTestConan(ConanFile):
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
        # 包内 msdl 绝对路径（conanrun 环境不保证 bin 在 PATH）
        msdl_bin = os.path.join(
            self.dependencies["msdl"].package_folder, "bin", "msdl")
        self.run(f"test -x {msdl_bin}")
        test_exe = os.path.join(self.cpp.build.bindir, "test_msdl")
        self.run(f"{test_exe} {msdl_bin}")
