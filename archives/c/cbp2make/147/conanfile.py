#!/usr/bin/env python3
"""Conan recipe — cbp2make 147 (Code::Blocks project to makefile converter, CLI tool).

cbp2make 将 Code::Blocks .cbp 工程文件转换为 Makefile（C++，ISO 标准，
随包 vendored tinyxml）。上游构建入口为 Code::Blocks 生成的
cbp2make.cbp.mak.unix，其中 CC/CXX/AR/LD 硬编码为 GNU 工具名，须以
make 命令行变量显式覆盖（命令行变量优先级高于 makefile 内赋值）。
上游无自动化测试套件（自带 tinyxml 的 xmltest.cpp 为第三方库样例，
未纳入 cbp2make 构建目标），消费者测试执行真实的 cbp→Makefile 转换。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Cbp2makeConan(ConanFile):
    name = "cbp2make"
    version = "147"
    description = "cbp2make — Code::Blocks project to makefile converter (CLI tool)"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/cbp2make/"
    url = "https://sourceforge.net/projects/cbp2make/"
    topics = ("codeblocks", "makefile", "converter", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # URL 为 sourceforge /download 中转链接（无扩展名），必须显式指定
        # 解压文件名，否则 conan 按默认 ZIP 处理报 BadZipFile（经验 §4.2）
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="cbp2make-stl-rev147.tar.gz")

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # 上游 makefile 硬编码 gcc/g++/ar，命令行变量覆盖（优先级高于
        # makefile 内赋值）；编译器路径来自 profile conf（R33 合规）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        cxx = compilers.get("cpp") if compilers else None
        if not cc or not cxx:
            raise ConanException("profile tools.build:compiler_executables must define c/cpp")
        tool_dir = os.path.dirname(cxx)
        ar = os.path.join(tool_dir, "llvm-ar")
        overrides = 'CC="%s" CXX="%s" AR="%s" LD="%s"' % (cc, cxx, ar, cxx)
        self.run(
            'make -f cbp2make.cbp.mak.unix release %s -j1' % overrides,
            cwd=self.source_folder, env="conanbuild")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "cbp2make", os.path.join(self.source_folder, "bin", "Release"),
             bindir, keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "usage.txt", self.source_folder,
             os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
