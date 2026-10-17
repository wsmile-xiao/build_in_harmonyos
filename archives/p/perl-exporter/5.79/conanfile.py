#!/usr/bin/env python3
"""Conan recipe for perl-exporter — 纯 Perl 符号导出模块 Exporter。

Exporter 实现默认 import 方法，允许模块导出函数/变量到用户命名空间
（perl 核心模块独立打包）。纯 Perl（lib/Exporter.pm + Heavy.pm），
META runtime requires 仅 Carp（核心模块），Test::Pod 为 recommends（可选）。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class ExporterConan(ConanFile):
    name = "perl-exporter"
    version = "5.79"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Exporter"
    description = "Exporter — implements default import method for modules (pure Perl)"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl——无编译——安装 lib/ 的 .pm 到 perl site-lib
        apply_conandata_patches(self)  # 无补丁时空操作

    def package(self):
        lib = os.path.join(self.source_folder, "lib")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(lib):
            shutil.copytree(lib, dest, dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
