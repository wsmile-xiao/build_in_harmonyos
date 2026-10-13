#!/usr/bin/env python3
"""test_package — libntfs-3g 2022.10.3 consumer test.

L1 test:
1. 编译 test.c 并链接 libntfs-3g（消费者视角，仅用已安装的头文件与库）；
2. 运行该二进制，其内部 6 条断言验证库核心 API（ntfs_malloc /
   ntfs_calloc / ntfs_free 与 ntfs_volume 结构体尺寸）。

上游无自带测试（R51 清点：make check 无 REGISTERED TESTS；GitHub 仓库树
test/check/torture 匹配数 0）——本测试为适配自研的消费者验证。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


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
        # 弱失败防线：交叉编译下若编译器未产出可执行文件（例如链接静默
        # 失败被吞），self.run 会因命令不存在而报错——此处显式校验，避免
        # 「跑了个不存在的程序」被误判为通过。
        if not os.path.isfile(exe):
            raise ConanException(
                f"consumer test binary not produced: {exe}")
        self.run(exe, env="conanrun")
