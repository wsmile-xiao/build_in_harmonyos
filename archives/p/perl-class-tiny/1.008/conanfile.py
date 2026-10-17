#!/usr/bin/env python3
"""Conan recipe for perl-class-tiny — 纯 Perl 极简类构造模块 Class::Tiny。

Class::Tiny 提供极简类构造（new/fields/accessors，约 120 行核心），
自动生成构造函数与字段访问器。纯 Perl（lib/Class/Tiny.pm），
META runtime requires 仅核心模块（Carp/strict/warnings/perl），
无外部 CPAN 依赖。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class ClassTinyConan(ConanFile):
    name = "perl-class-tiny"
    version = "1.008"
    package_type = "application"
    license = "Apache-2.0"
    homepage = "https://metacpan.org/pod/Class::Tiny"
    description = "Class::Tiny — minimalist class construction (pure Perl)"
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
