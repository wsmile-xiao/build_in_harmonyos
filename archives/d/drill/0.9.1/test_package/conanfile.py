#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class DrillTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        """检查 drill 二进制是否已安装到 package 中"""
        binary = os.path.join(self.dependencies["drill"].package_folder, "bin", "drill")
        if os.path.exists(binary):
            self.output.info(f"drill binary found: {binary}")
            return True
        self.output.error(f"drill binary not found at {binary}")
        return False

    def test(self):
        binary_ok = self._check_binary_exists()
        if not binary_ok:
            raise Exception("drill binary not found in package")

        # 编译测试源文件（shell $CC/$CFLAGS 来自 VirtualBuildEnv）
        src = os.path.join(self.source_folder, "src", "test_drill.c")
        test_bin = os.path.join(self.build_folder, "test_drill")
        ret = self.run(f'${{CC:-clang}} ${{CFLAGS}} -o "{test_bin}" "{src}"', env="conanbuild")
        if ret != 0:
            raise ConanException(f"test_drill.c compilation failed with exit code {ret}")

        if can_run(self):
            # 运行测试程序验证 drill --help 输出
            drill_bin = os.path.join(self.dependencies["drill"].package_folder, "bin", "drill")
            ret = self.run(f'"{test_bin}" "{drill_bin}"', env="conanrun")
            if ret != 0:
                raise ConanException(f"test_drill run failed with exit code {ret}")
            self.output.info("drill binary verified successfully")
        else:
            self.output.info("Cross-building: test compiled, binary existence verified")