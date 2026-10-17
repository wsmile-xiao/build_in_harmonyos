#!/usr/bin/env python3
"""Conan recipe for perl-text-csv — 纯 Perl CSV 处理模块 Text::CSV。

Text::CSV 是 CSV 组合/分解模块的薄封装：默认加载 Text::CSV_XS（XS），
不可用时回退到本发行捆绑的 Text::CSV_PP（纯 Perl）。本配方打包
lib/Text/CSV.pm + lib/Text/CSV_PP.pm，运行时用 PERL_TEXT_CSV=0 强制
PP 后端（无 XS 编译，规避 hmmac dlopen .so 限制——E212 类问题）。
META runtime requires 仅核心模块（IO::Handle/Test::Harness/Test::More/
perl），无外部 CPAN 依赖；Text::CSV_XS 是 recommends（可选，未安装即回退 PP）。
package_type=application（python-require 型 conan create 静默跳过构建——
perl-algorithm-diff/dataproperty/pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class TextCsvConan(ConanFile):
    name = "perl-text-csv"
    version = "2.06"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Text::CSV"
    description = "Text::CSV — comma-separated values manipulator (pure Perl, PP backend)"
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
