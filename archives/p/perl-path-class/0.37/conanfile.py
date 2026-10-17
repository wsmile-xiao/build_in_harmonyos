#!/usr/bin/env python3
"""Conan recipe for perl-path-class — 纯 Perl 路径操作模块 Path::Class。

Path::Class 提供跨平台路径规范操作（file/dir 对象，支持 contains/subsumes/
traverse 等）。纯 Perl（lib/Path/Class.pm + Dir.pm + Entity.pm + File.pm），
META runtime requires 全部为核心模块（Carp/Cwd/Exporter/File::Copy/
File::Path/File::Spec/File::Temp/File::stat/IO::Dir/IO::File/Perl::OSType/
Scalar::Util/overload/parent/strict/warnings），无外部 CPAN 依赖。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class PathClassConan(ConanFile):
    name = "perl-path-class"
    version = "0.37"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Path::Class"
    description = "Path::Class — cross-platform path specification manipulation (pure Perl)"
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
