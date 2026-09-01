#!/usr/bin/env python3
"""Conan recipe for perl-getopt-long — 纯 Perl 命令行参数解析模块 Getopt::Long。

Getopt::Long 实现扩展 getopt 函数 GetOptions()，解析 @ARGV 命令行选项。
纯 Perl（lib/Getopt/Long.pm + Parser.pm），无编译、无外部 CPAN 依赖
（依赖 perl 核心模块，如 perl/Pod::Usage 等）。Getopt::Long 是 perl 核心
模块，本配方将其作为独立 CPAN 发行打包供下游引用。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class GetoptLongConan(ConanFile):
    name = "perl-getopt-long"
    version = "2.58"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Getopt::Long"
    description = "Getopt::Long — extended processing of command line options (pure Perl)"
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
