#!/usr/bin/env python3
"""Conan recipe for perl-file-which — 纯 Perl which 工具 API 实现 File::Which。

File::Which 以 API 形式实现 which 命令（按 PATH 查找可执行文件），
纯 Perl（lib/File/Which.pm），META runtime requires 仅核心模块
（base/perl），无外部 CPAN 依赖。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class FileWhichConan(ConanFile):
    name = "perl-file-which"
    version = "1.27"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/File::Which"
    description = "File::Which — Perl implementation of the which utility as an API (pure Perl)"
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
