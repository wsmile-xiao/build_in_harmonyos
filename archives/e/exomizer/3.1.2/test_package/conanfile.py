#!/usr/bin/env python3
"""Conan test_package for exomizer 3.1.2 — real-binary roundtrip consumer test.

R34 合规:测试真实执行被测包二进制,不做空壳打印。test_exomizer.c 调用
exomizer 完成 raw 压缩 → raw 解压 → 字节级比对,任一环节失败即非零退出。
"""
import os

from conan import ConanFile


class ExomizerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 编译消费者载体（L0c: test_package 需含测试源文件）
        test_c = os.path.join(self.source_folder, "test_exomizer.c")
        assert os.path.isfile(test_c), f"test_exomizer.c missing at {test_c}"
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("cc") or compilers.get("c") or "clang"
        self.run(f"{cc} {test_c} -o test_exomizer")

    def test(self):
        exo = self.dependencies["exomizer"]
        bin_path = os.path.join(exo.package_folder, "bin", "exomizer")
        sample = os.path.join(self.source_folder, "sample.bin")
        # 有意义的输入:重复模式 + 序列段;体积与上游 Makefile.test 的
        # vec.h 同级(数 KB)。注意:exomizer 是 optimal 压缩器,大输入会
        # 指数级变慢(46KB 样本在 x86_64 主机 >300s),必须用小样本。
        with open(sample, "wb") as f:
            f.write(b"Hello HarmonyOS PC! " * 64)
            f.write(bytes(range(128)) * 8)
        out_dir = os.path.join(self.build_folder, "roundtrip")
        os.makedirs(out_dir, exist_ok=True)
        self.run(f'./test_exomizer "{bin_path}" "{sample}" "{out_dir}"')
