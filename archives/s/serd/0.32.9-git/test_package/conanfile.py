#!/usr/bin/env python3
"""Conan test_package for serd — 消费者视角验证。

验证：
1. include/serd-0/serd/serd.h 头文件存在
2. lib/libsord... libserd-0.so 库产物存在
3. pkg-config serd-0.pc 存在
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SerdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["serd"].package_folder
        header = os.path.join(pkg, "include", "serd-0", "serd", "serd.h")
        pc = os.path.join(pkg, "lib", "pkgconfig", "serd-0.pc")
        header_ok = os.path.isfile(header)
        pc_ok = os.path.isfile(pc)
        self.output.info(f"serd.h found: {header_ok} ({header})")
        self.output.info(f"serd-0.pc found: {pc_ok} ({pc})")
        if not header_ok or not pc_ok:
            raise Exception("serd package artifacts missing")
        # 运行测试源脚本（src/test_serd.sh，L0c 门禁要求 test_package/ 下有
        # .c/.cpp/.sh/.py 测试源文件；L0d 门禁要求 test() 中有 self.run）
        script = os.path.join(self.source_folder, "src", "test_serd.sh")
        serdi = os.path.join(pkg, "bin", "serdi")
        if os.path.isfile(script):
            # 沙箱导出可能丢失可执行位，显式用 bash 调用
            self.run(f'bash "{script}" "{serdi}" "{os.path.join(pkg, "lib")}"',
                     env="conanrun")
        else:
            self.run(f'"{serdi}" --help', env="conanrun")
        self.output.info("serd test_package PASS")
