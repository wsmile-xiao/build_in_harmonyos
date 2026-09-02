#!/usr/bin/env python3
"""Conan recipe for perl-config-tiny — 纯 Perl .ini 配置读写模块 Config::Tiny。

Config::Tiny 以最少代码读写 .ini 风格配置文件（read/write），
纯 Perl（lib/Config/Tiny.pm），META runtime requires 仅核心模块
（File::Spec/File::Temp/strict/utf8/perl），无外部 CPAN 依赖。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class ConfigTinyConan(ConanFile):
    name = "perl-config-tiny"
    version = "2.30"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Config::Tiny"
    description = "Config::Tiny — read/write .ini style files with as little code as possible (pure Perl)"
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
