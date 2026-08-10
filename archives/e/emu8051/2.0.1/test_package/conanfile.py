#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.build import can_run


class Emu8051TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        """检查 emu8051 二进制是否已安装到 package 中"""
        binary = os.path.join(self.dependencies["emu8051"].package_folder, "usr", "bin", "emu")
        if os.path.exists(binary):
            self.output.info(f"emu8051 binary found: {binary}")
            return True
        self.output.error(f"emu8051 binary not found at {binary}")
        return False

    def test(self):
        # 始终检查二进制产物是否存在（交叉编译和 native 都适用）
        binary_ok = self._check_binary_exists()
        if not binary_ok:
            raise Exception("emu8051 binary not found in package")

        # 编译测试源文件（C 编译器标识符 gcc/clang 均是对应二进制名）
        cc = str(self.settings.compiler)
        src = os.path.join(self.source_folder, "src", "test_emu8051.c")
        test_bin = os.path.join(self.build_folder, "test_emu8051")
        self.run(f"{cc} -o {test_bin} {src}")

        if can_run(self):
            # 运行测试程序验证 emu8051 二进制可执行（--help 输出）
            emu_bin = os.path.join(self.dependencies["emu8051"].package_folder, "usr", "bin", "emu")
            self.run(f"{test_bin} {emu_bin}")
            self.output.info("emu8051 binary verified successfully")
        else:
            # 交叉编译场景：无法运行二进制，但已编译测试程序并检查产物存在
            self.output.info("Cross-building: test compiled, binary existence verified")