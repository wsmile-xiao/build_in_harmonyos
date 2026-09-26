#!/usr/bin/env python3
"""Conan test_package — kic 2.4c 鸿蒙消费者端到端测试 (R34 + 鸿蒙用例).

手动编译 test.c（不依赖 CMake 生成器），以 -D 注入被测二进制与启动
文件目录路径；test() 用 self.run() 执行（满足 L0c 测试源 + L0d
self.run 门禁）。测试在 OHOS 设备上真实执行 ciftokic/kictocif 完成
CIF→kic→CIF 端到端转换链路验证。
"""
import os

from conan import ConanFile


class KicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["kic"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        ciftokic = os.path.join(bin_dir, "ciftokic")
        kictocif = os.path.join(bin_dir, "kictocif")
        libdir = os.path.join(dep.package_folder, "lib", "kic")
        self.output.info(f"ciftokic: {ciftokic}")
        self.output.info(f"kictocif: {kictocif}")
        cc = os.environ.get("CC", "clang")
        self.run(
            f"{cc} -O2 -Wall test.c -o test_kic "
            f"-DCIFTOKIC='\"{ciftokic}\"' "
            f"-DKICTOCIF='\"{kictocif}\"' "
            f"-DKIC_LIBDIR='\"{libdir}\"'"
        )

    def test(self):
        # L0d 门禁要求 test() 调用 self.run() 执行测试程序
        self.run("./test_kic")
