#!/usr/bin/env python3
"""Conan recipe for perl-test-harness — Perl 测试驱动框架（TAP::* / prove）。

Test::Harness 提供 TAP::Harness / TAP::Parser / App::Prove 及 bin/prove
命令行工具。纯 Perl（无编译），META.json runtime requires 为空（仅依赖
核心模块）。package_type=application（本环境 python-require 型 conan
create 静默跳过构建——dataproperty/pytablewriter 先例），需配套
commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class TestHarnessConan(ConanFile):
    name = "perl-test-harness"
    version = "3.52"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Test::Harness"
    description = "Test::Harness — run Perl standard test scripts with statistics (pure Perl)"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl——无编译——安装 lib/ 的 .pm 到 perl site-lib
        pass

    def package(self):
        # Perl 模块：lib/**/*.pm → lib/perl5/
        lib = os.path.join(self.source_folder, "lib")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(lib):
            shutil.copytree(lib, dest, dirs_exist_ok=True)
        # 可执行脚本：bin/prove → bin/
        prove_src = os.path.join(self.source_folder, "bin", "prove")
        bin_dest = os.path.join(self.package_folder, "bin")
        if os.path.isfile(prove_src):
            os.makedirs(bin_dest, exist_ok=True)
            shutil.copy2(prove_src, os.path.join(bin_dest, "prove"))

    def package_info(self):
        self.cpp_info.libs = []
