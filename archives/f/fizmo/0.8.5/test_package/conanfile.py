#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class FizmoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        """检查 fizmo-ncursesw 二进制是否已安装到 package 中"""
        binary = os.path.join(self.dependencies["fizmo"].package_folder, "bin", "fizmo-ncursesw")
        if os.path.exists(binary):
            self.output.info(f"fizmo-ncursesw binary found: {binary}")
            return True
        self.output.error(f"fizmo-ncursesw binary not found at {binary}")
        return False

    def test(self):
        binary_ok = self._check_binary_exists()
        if not binary_ok:
            raise Exception("fizmo-ncursesw binary not found in package")

        # 编译测试源文件（shell $CC/$CFLAGS 来自 VirtualBuildEnv）
        src = os.path.join(self.source_folder, "src", "test_fizmo.c")
        test_bin = os.path.join(self.build_folder, "test_fizmo")
        ret = self.run(f'${{CC:-clang}} ${{CFLAGS}} -o "{test_bin}" "{src}"', env="conanbuild")
        if ret != 0:
            raise ConanException(f"test_fizmo.c compilation failed with exit code {ret}")

        if can_run(self):
            # 运行测试程序验证 fizmo-ncursesw --help 输出
            fizmo_bin = os.path.join(self.dependencies["fizmo"].package_folder, "bin", "fizmo-ncursesw")
            ret = self.run(f'"{test_bin}" "{fizmo_bin}"', env="conanrun")
            if ret != 0:
                raise ConanException(f"test_fizmo run failed with exit code {ret}")
            self.output.info("fizmo-ncursesw binary verified successfully")
        else:
            self.output.info("Cross-building: test compiled, binary existence verified")