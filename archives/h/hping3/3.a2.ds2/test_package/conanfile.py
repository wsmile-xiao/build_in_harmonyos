#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.build import can_run


class Hping3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        """检查 hping3 二进制是否安装到 package 中"""
        binary = os.path.join(self.dependencies["hping3"].package_folder, "bin", "hping3")
        if os.path.exists(binary):
            self.output.info(f"hping3 binary found: {binary}")
            return True
        self.output.error(f"hping3 binary not found at {binary}")
        return False

    def test(self):
        binary_ok = self._check_binary_exists()

        if can_run(self):
            # 编译 test_hping3.c
            cc = os.environ.get("CC", str(self.settings.compiler))
            src = os.path.join(self.source_folder, "src", "test_hping3.c")
            bin_path = os.path.join(self.build_folder, "test_hping3")
            self.run(f"{cc} -o {bin_path} {src}", env="conanbuild")

            # 通过完整路径验证 hping3 可执行
            hping3_bin = os.path.join(self.dependencies["hping3"].package_folder, "bin", "hping3")
            self.run(f"{hping3_bin} --version", env="conanrun")
            self.run(f"{bin_path} {hping3_bin}", env="conanrun")
        else:
            # 交叉编译场景：无法运行二进制，仅验证产物存在
            if not binary_ok:
                raise Exception("hping3 binary not found in package")
            self.output.info("Cross-building: skipping runtime tests, binary existence verified")
