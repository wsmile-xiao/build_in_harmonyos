#!/usr/bin/env python3
"""Conan recipe for perl-text-diff — 纯 Perl 模块 Text::Diff（无编译）。

Text::Diff 计算两文本/记录集的差异（perl 的 GNU diff 风格实现）。纯 Perl
（lib/Text/Diff.pm + Config.pm + Table.pm），META runtime requires:
Algorithm::Diff(>=1.19, 已发布 perl-algorithm-diff/1.1903)、Exporter(核心)。
package_type=application（本环境 python-require 型 conan create 静默
跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 先例），
需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class TextDiffConan(ConanFile):
    name = "perl-text-diff"
    version = "1.45"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Text::Diff"
    description = "Text::Diff — perform diffs on files and record sets (pure Perl)"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Algorithm::Diff 已发布 perl-algorithm-diff/1.1903（ohpcd + main）
        self.requires("perl-algorithm-diff/1.1903")

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
