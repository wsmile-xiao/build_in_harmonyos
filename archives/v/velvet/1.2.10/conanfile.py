#!/usr/bin/env python3
"""Conan recipe — velvet 1.2.10 (Makefile CLI tools)

Upstream: https://github.com/dzerbino/velvet (tag v1.2.10)
Velvet 是经典的 de Bruijn 图短读序列组装器（Zerbino & Birney 2008），
产物为两个 CLI 可执行文件: velveth（k-mer 哈希）与 velvetg（图组装）。

构建系统: 上游手写 Makefile（无 configure）。
  - CC/CFLAGS/LDFLAGS 均可通过 make 命令行覆盖（CFLAGS 命令行覆盖同时
    去掉上游硬编码的 -m64，无需补丁）；
  - 链接 -lz，依赖 zlib/1.3.1.1（制品仓已发布），头文件/库路径经
    CFLAGS/LDFLAGS 注入，不使用 BUNDLEDZLIB（third-party/zlib-1.2.3）。

上游测试: tests/run-tests.sh（5 个 .t 用例，Makefile test 目标入口）。
在 build() 末尾通过显式 bash 调用执行（can_run 守卫：OHOS worker 原生
执行；macOS 开发机交叉编译时跳过）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class VelvetConan(ConanFile):
    name = "velvet"
    version = "1.2.10"
    description = "Sequence assembler for very short reads using de Bruijn graphs"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/dzerbino/velvet"
    url = "https://github.com/dzerbino/velvet"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 制品仓已发布（W0 conan download --only-recipe 探测通过）: zlib/1.3.1.1
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器取自 Conan conf，禁止从 shell 环境取
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        zlib = self.dependencies["zlib"]
        extra_incs = " ".join(f"-I{p}" for p in zlib.cpp_info.includedirs)
        extra_libs = " ".join(f"-L{p}" for p in zlib.cpp_info.libdirs)
        # 命令行覆盖 CFLAGS 可同时剔除上游硬编码的 -m64（aarch64 无意义），
        # 显式指定 velveth/velvetg 目标以跳过 doc（需要 pdflatex）。
        # R9: OHOS 平台使用 -j1。
        self.run(
            f'make -j1 velveth velvetg CC={cc} '
            f'CFLAGS="-Wall {extra_incs}" LDFLAGS="{extra_libs}"',
            cwd=self.source_folder,
        )
        # L1: 上游官方测试套件（make test 入口为 tests/run-tests.sh）。
        # 显式用 bash 调用，避免依赖 OHOS 上 /usr/bin/env 对 bash 的解析。
        # can_run=False（macOS 交叉编译）时跳过，由 OHOS CI worker 原生执行。
        # 注意：run-tests.sh 以 ../velveth 相对路径取二进制，必须在 tests/
        # 目录内执行（等价于 make test 的 cd tests && ./run-tests.sh）。
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'"{bash}" run-tests.sh',
                     cwd=os.path.join(self.source_folder, "tests"))

    def package(self):
        for tool in ("velveth", "velvetg"):
            copy(self, tool, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
