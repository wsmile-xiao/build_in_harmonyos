#!/usr/bin/env python3
"""test_package — libgsf 1.14.5 consumer test (R34).

L1 test:
1. 编译并运行 test.c（链接 libgsf-1，gzip 内存解压验证库可用）；
2. 应用验证：libgsf-1 库文件存在。
"""
import os

from conan import ConanFile


class LibgsfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libgsf 头文件依赖 glib 头；链接 -lintl 需 gettext 包路径——
        # 显式 requires 使 package_folder 在 build() 可用
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")
        self.requires("gettext/0.22.5")

    def build(self):
        # TMPDIR 注入（同主配方）：鸿蒙安全框架拦 clang 在不可写目录创建
        # 临时文件（"unable to make temporary file"）——注入 build 目录内
        # 可写 .conan_tmp
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_libgsf")
        pkg = self.dependencies["libgsf"].package_folder
        glib_pkg = self.dependencies["glib"].package_folder
        xml_pkg = self.dependencies["libxml2"].package_folder
        z_pkg = self.dependencies["zlib"].package_folder
        # gettext 为 libgsf 传递依赖（提供 libintl，解析 libgsf-1.so 的
        # gettext 符号）
        gt_pkg = self.dependencies["gettext"].package_folder
        self.run(
            f"{cc} {src} -o {out} "
            f"-I{pkg}/include/libgsf-1 "
            f"-I{glib_pkg}/include/glib-2.0 "
            f"-I{glib_pkg}/lib/glib-2.0/include "
            f"-I{xml_pkg}/include/libxml2 "
            f"-L{pkg}/lib -L{glib_pkg}/lib -L{xml_pkg}/lib -L{z_pkg}/lib "
            f"-L{gt_pkg}/lib "
            f"-lgsf-1 -lxml2 "
            # 注意：glib 为静态库且已被静态链入 libgsf-1.so——test 再静态
            # 链 glib 会产生双 glib 实例（GType 注册表冲突，运行时段错误）。
            # 仅链接动态库（libgsf-1/libxml2），glib 符号由 libgsf-1.so
            # 内部解析（其 DT_NEEDED 含 libc/libxml2）。
        )

    def test(self):
        exe = os.path.join(self.build_folder, "test_libgsf")
        self.run(exe, env="conanrun")
