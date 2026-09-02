#!/usr/bin/env python3
"""Conan recipe for perl-test-exception — 纯 Perl 异常测试模块 Test::Exception。

Test::Exception 提供 throws_ok/lives_ok/dies_ok 等便捷方法测试异常代码，
基于 Test::Builder 构建，与 Test::More 兼容。纯 Perl（lib/Test/Exception.pm），
META runtime requires: Sub::Uplevel(>=0.18，已发布 perl-sub-uplevel/0.2800)
+ 核心模块（Carp/Exporter/Test::Builder/Test::Builder::Tester/Test::Harness）。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class TestExceptionConan(ConanFile):
    name = "perl-test-exception"
    version = "0.43"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Test::Exception"
    description = "Test::Exception — test exception-based code (pure Perl)"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Sub::Uplevel 已发布 perl-sub-uplevel/0.2800（ohpcd + main）
        self.requires("perl-sub-uplevel/0.2800")

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
