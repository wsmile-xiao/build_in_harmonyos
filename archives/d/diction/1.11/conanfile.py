#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# conanfile.py — diction 1.11 (HarmonyOS PC / aarch64)

import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class DictionConan(ConanFile):
    name = "diction"
    version = "1.11"
    description = "GNU diction prints wordy and commonly misused phrases found in a text"
    license = "GPL-3.0-or-later"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://www.gnu.org/software/diction/"
    topics = ("gnu", "style-checker", "text-processing", "command-line")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/**"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # 上游 Makefile 只支持 in-source 构建，且测试脚本 test/test01..test09 会在
        # 当前目录读写 ./diction、./test.in，因此采用 in-source 布局。
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # diction 在 configure 阶段把短语库目录编译进二进制（SHAREDIR），
        # --prefix 指向 package_folder 使默认查找路径与安装布局一致。
        self.run(f"./configure --prefix={self.package_folder}", env="conanbuild",
                 cwd=self.source_folder)
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)

        # 上游测试套件（test01..test09）：Makefile 的 check 目标在第一个失败处 break
        # 且仍然返回 0，无法作为通过证据，故逐个执行各测试脚本获取真实结果。
        tests = sorted(glob.glob(os.path.join(self.source_folder, "test", "test0*")))
        for test in tests:
            name = os.path.basename(test)
            if self.run(f"sh ./test/{name}", ignore_errors=True, env="conanbuild",
                        cwd=self.source_folder) != 0:
                raise ConanException(f"upstream test {name} failed")
        self.output.info(f"upstream test suite: {len(tests)} tests passed")

    def package(self):
        # --prefix 已在 configure 阶段指向 package_folder，安装时不能再叠加
        # Conan 默认的 DESTDIR（否则会写成 package_folder/package_folder）。
        autotools = Autotools(self)
        autotools.make(target="install")
        copy(self, "README-LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 命令行工具（diction / style）：可执行文件位于 bin/
        self.cpp_info.bindirs = ["bin"]
        # 运行时数据：短语库 share/diction/
        self.cpp_info.resdirs = ["share/diction"]
