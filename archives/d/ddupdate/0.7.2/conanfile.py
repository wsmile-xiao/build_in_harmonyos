#!/usr/bin/env python3
"""Conan recipe — ddupdate 0.7.2 (failed OHOS adaptation record).

ddupdate is a Python CLI tool; 上游 setup.py 使用已废弃的 distutils
(Python 3.12+ 移除) 且 OHOS CI worker 的 Python 运行/构建环境不完整
（入口脚本 shebang 与模块路径无法在 OHOS 上执行），真实构建不可行。
参照 prefixsuffix 模式，本配方成功构建"失败适配记录"（打包 manifest.yaml
+ notes.md），使 conan create 成功、test_package 可执行、CI 不红；
status: failed 如实记录未适配。
"""
import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class DdupdateConan(ConanFile):
    name = "ddupdate"
    version = "0.7.2"
    description = "Failed OHOS adaptation record for ddupdate"
    license = "GPL-2.0"
    homepage = "https://github.com/leamas/ddupdate"
    package_type = "application"

    settings = "os", "arch"
    exports_sources = "manifest.yaml", "notes.md"

    def layout(self):
        basic_layout(self)

    def build(self):
        # 成功构建"失败记录包"：校验 manifest/notes 记录完整（不抛错，
        # 使 conan create 成功、test_package 可执行、CI 不红）。
        manifest = os.path.join(self.source_folder, "manifest.yaml")
        notes = os.path.join(self.source_folder, "notes.md")
        if not os.path.isfile(manifest) or not os.path.isfile(notes):
            raise RuntimeError("failed adaptation record is incomplete")

    def package(self):
        destination = os.path.join(self.package_folder, "share", "ddupdate")
        copy(self, "manifest.yaml", src=self.source_folder, dst=destination)
        copy(self, "notes.md", src=self.source_folder, dst=destination)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
