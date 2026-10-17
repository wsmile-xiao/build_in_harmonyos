#!/usr/bin/env python3
"""Conan recipe — pscan 1.3 (C 源码 printf 格式串滥用静态扫描器).

上游为 ~100 行 C 的小工具(Alan DeKok,FreeRADIUS 作者),flex 词法 +
手写 Makefile。上游官网(dwheeler.com/pscan 与 deployingradius.com/pscan)
均已失效,源码取 Debian pool 的未修改 orig.tar(上游源码的权威分发渠道,
见 PR 描述说明)。tarball 为无顶层目录的平铺结构,strip_root=False。

构建:tool_requires flex/2.6.4 生成 scanner.yy.c,再编译两文件。无上游
测试套件(README 自述),验证由 test_package 消费者测试承担:用上游自带
test.c(故意标注 good/bad)作扫描输入断言检出行为(jpnevulator 0/0 先例)。
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get


class PscanConan(ConanFile):
    name = "pscan"
    version = "1.3"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        src = self.source_folder
        # 1) flex 生成词法器
        self.run("flex -t scanner.l > scanner.yy.c", cwd=src, env="conanbuild")
        # 2) 编译(Host C 编译器来自 profile)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        self.run(f'"{cc}" -O2 scanner.yy.c pscan.c -o pscan', cwd=src, env="conanbuild")

    def package(self):
        src = self.source_folder
        copy(self, "pscan", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "test.c", src=src, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.define_path("PATH", bindir)
