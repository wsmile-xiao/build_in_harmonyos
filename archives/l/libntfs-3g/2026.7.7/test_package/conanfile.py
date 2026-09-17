#!/usr/bin/env python3
"""test_package — libntfs-3g 2026.7.7 consumer test (R34).

L1 test:
1. 编译并运行 test.c（链接 libntfs-3g，调用库 API）；
2. 应用验证：libntfs-3g 库文件存在。

上游无自带测试（R51：make check 无 REGISTERED TESTS、GitHub 仓库树
test/check/torture 匹配数 0）——本测试为适配自研的消费者验证。
"""
import os

from conan import ConanFile


class Libntfs3gTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # TMPDIR 注入（同主配方）：鸿蒙安全框架拦 clang 在不可写目录
        # 创建临时文件
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_libntfs-3g")
        pkg = self.dependencies["libntfs-3g"].package_folder
        self.run(
            f"{cc} {src} -o {out} "
            f"-I{pkg}/include "
            f"-L{pkg}/lib -lntfs-3g -lpthread"
        )

    def test(self):
        exe = os.path.join(self.build_folder, "test_libntfs-3g")
        self.run(exe, env="conanrun")