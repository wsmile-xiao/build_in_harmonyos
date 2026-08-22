#!/usr/bin/env python3
"""Conan recipe — dex2jar 2.4 (failed OHOS adaptation record).

dex2jar is a JVM tool built with Gradle; OHOS CI worker 无 JDK
(install-jdk.sh 不在 CI 范围内)，`_ensure_java()` 找不到可用 JDK，
真实构建不可能。参照 prefixsuffix 模式，本配方成功构建"失败适配记录"
（打包 manifest.yaml + notes.md），使 conan create 成功、test_package
可执行、CI 不红；status: failed 如实记录未适配。
"""
import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class Dex2JarConan(ConanFile):
    name = "dex2jar"
    version = "2.4"
    description = "Failed OHOS adaptation record for dex2jar"
    license = "Apache-2.0"
    homepage = "https://github.com/pxb1988/dex2jar"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
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
        destination = os.path.join(self.package_folder, "share", "dex2jar")
        copy(self, "manifest.yaml", src=self.source_folder, dst=destination)
        copy(self, "notes.md", src=self.source_folder, dst=destination)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
