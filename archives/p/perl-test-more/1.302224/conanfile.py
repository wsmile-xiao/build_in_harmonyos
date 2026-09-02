#!/usr/bin/env python3
"""Conan recipe for perl-test-more — 纯 Perl 测试模块 Test::More。

Test::More 提供丰富的测试断言（ok/is/isnt/like/cmp_ok/done_testing 等），
是 CPAN 模块测试事实标准。本包与 perl-test-simple 同源——两者均来自
Test-Simple 发行（Test-Simple-1.302224.tar.gz 同时提供 Test::Simple 和
Test::More），本包按 perl-test-more 名适配、打包 Test::More 供下游引用。
纯 Perl（lib/Test/More.pm + Test/Builder + Test2/* 等），无编译，无外部
CPAN 依赖（META runtime requires 全部为核心模块）。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class TestMoreConan(ConanFile):
    name = "perl-test-more"
    version = "1.302224"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Test::More"
    description = "Test::More — yet another framework for writing test scripts (pure Perl, Test-Simple dist)"
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
