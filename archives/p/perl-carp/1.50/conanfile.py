#!/usr/bin/env python3
"""Conan recipe for perl-carp — 纯 Perl 警告/错误报告模块 Carp。

Carp 提供 carp/croak/cluck/confess/longmess 等替代 warn/die 的报错方式，
从模块调用者的角度报告错误位置（perl 核心模块独立打包）。
纯 Perl（lib/Carp.pm + Heavy.pm），META runtime requires 仅核心模块
（perl/Exporter/overload/warnings/strict 等），无外部 CPAN 依赖。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class CarpConan(ConanFile):
    name = "perl-carp"
    version = "1.50"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Carp"
    description = "Carp — alternative warn and die for modules (pure Perl)"
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
