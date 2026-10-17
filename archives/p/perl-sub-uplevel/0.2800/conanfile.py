#!/usr/bin/env python3
"""Conan recipe for perl-sub-uplevel — 纯 Perl 模块 Sub::Uplevel（无编译）。

Sub::Uplevel 让被测代码的 caller() 看到外层调用栈（Test::Exception 依赖）。
纯 Perl（lib/Sub/Uplevel.pm），依赖仅 Perl 核心模块（Carp/constant）。
package_type=application（本环境 python-require 型 conan create 静默跳过
构建——dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class SubUplevelConan(ConanFile):
    name = "perl-sub-uplevel"
    version = "0.2800"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Sub::Uplevel"
    description = "Sub::Uplevel — apparently run stuff in a higher stack frame (pure Perl)"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl 模块——无编译——安装 lib/ 的 .pm 到 perl site-lib
        pass

    def package(self):
        lib = os.path.join(self.source_folder, "lib")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(lib):
            shutil.copytree(lib, dest, dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
