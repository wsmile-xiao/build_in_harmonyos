#!/usr/bin/env python3
"""Conan recipe for perl-test-simple — 纯 Perl 测试模块 Test::Simple。

Test-Simple 发行提供 Test::Simple/Test::More/Test2/Test::Builder 等一整套
测试工具（perl 核心双生命周期模块独立打包）。纯 Perl（lib/ 下大量 .pm，
含 Test/Simple.pm + Test/More.pm + Test2/*），无编译。
META runtime requires 全部为核心模块（perl 核心分发），无外部 CPAN 依赖。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class TestSimpleConan(ConanFile):
    name = "perl-test-simple"
    version = "1.302224"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Test::Simple"
    description = "Test::Simple — basic utilities for writing tests (pure Perl, Test-Simple dist)"
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
