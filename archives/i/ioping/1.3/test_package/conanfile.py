#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.build import can_run


class IopingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        """检查 ioping 二进制是否已安装到 package 中"""
        binary = os.path.join(self.dependencies["ioping"].package_folder, "usr", "bin", "ioping")
        if os.path.exists(binary):
            self.output.info(f"ioping binary found: {binary}")
            return True
        self.output.error(f"ioping binary not found at {binary}")
        return False

    def test(self):
        # 始终检查二进制产物是否存在（交叉编译和 native 都适用）
        binary_ok = self._check_binary_exists()

        if can_run(self):
            # 编译 test_ioping.c
            cc = str(self.settings.compiler)
            src = os.path.join(self.source_folder, "src", "test_ioping.c")
            bin_path = os.path.join(self.build_folder, "test_ioping")
            self.run(f"{cc} -o {bin_path} {src}")

            # 通过完整路径验证 ioping 二进制可执行
            ioping_bin = os.path.join(self.dependencies["ioping"].package_folder, "usr", "bin", "ioping")
            self.run(f"{ioping_bin} --version")
            self.run(f"{ioping_bin} --help")

            # 执行 test_ioping 验证程序（传入 ioping 完整路径）
            self.run(f"{bin_path} {ioping_bin}")
        else:
            # 交叉编译场景：无法运行二进制，但已检查产物存在
            if not binary_ok:
                raise Exception("ioping binary not found in package")
            self.output.info("Cross-building: skipping runtime tests, binary existence verified")
