#!/usr/bin/env python3
"""Conan recipe for perl-json-tiny — 纯 Perl 极简 JSON 编解码模块 JSON::Tiny。

JSON::Tiny 是 Mojo::JSON 的独立极简适配（单文件 <300 行，仅核心依赖），
提供 encode_json/decode_json 等。纯 Perl（lib/JSON/Tiny.pm），
META runtime requires 仅 perl 核心，JSON::PP 为 suggests（可选）。
无外部 CPAN 依赖。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class JsonTinyConan(ConanFile):
    name = "perl-json-tiny"
    version = "0.58"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/JSON::Tiny"
    description = "JSON::Tiny — minimalistic JSON, no dependencies (pure Perl)"
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
