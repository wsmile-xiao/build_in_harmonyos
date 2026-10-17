#!/usr/bin/env python3
"""test_package — baitfisher 1.2.7 consumer test (R34).

L1 test:
1. 编译并运行 test.c（L0c 测试源文件载体）；
2. 应用验证：BaitFisher/BaitFilter 可执行存在并运行（输出用法）。
"""
import os

from conan import ConanFile


class BaitfisherTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_baitfisher")
        self.run(f"{cc} {src} -o {out}")

    def test(self):
        exe = os.path.join(self.build_folder, "test_baitfisher")
        bindir = os.path.join(
            self.dependencies["baitfisher"].package_folder, "bin")
        bf = os.path.join(bindir, "BaitFisher-v1.2.8")
        bl = os.path.join(bindir, "BaitFilter-v1.0.6")
        self.run(f"test -x {bf}")
        self.run(f"test -x {bl}")
        # test.c 执行 BaitFisher 无参数运行并断言输出含 Usage（R34 非空壳）
        self.run(f"{exe} {bf}", env="conanrun")
