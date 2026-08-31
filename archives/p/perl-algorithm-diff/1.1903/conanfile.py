#!/usr/bin/env python3
"""Conan recipe for perl-algorithm-diff — 纯 Perl 模块 Algorithm::Diff（无编译）。

Algorithm::Diff 计算两序列之间的差异（Text::Diff 依赖）。纯 Perl
（lib/Algorithm/Diff.pm + DiffOld.pm），META.json runtime requires 为空。
package_type=application（本环境 python-require 型 conan create 静默
跳过构建——dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class AlgorithmDiffConan(ConanFile):
    name = "perl-algorithm-diff"
    version = "1.1903"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Algorithm::Diff"
    description = "Algorithm::Diff — compute 'intelligent' differences between two files (pure Perl)"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl——无编译——安装 lib/ 的 .pm 到 perl site-lib
        pass

    def package(self):
        lib = os.path.join(self.source_folder, "lib")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(lib):
            shutil.copytree(lib, dest, dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
