#!/usr/bin/env python3
"""Conan recipe for perl-io-multiplex 1.16 — IO::Multiplex
(pure-Perl module, CPAN source, dependency: IO::Socket (perl core)).

Pure-Perl module: build via perl Makefile.PL → make → make install
DESTDIR into the conan package folder; consumers add site/lib to PERL5LIB.
NOTE: make install paths carry the full perl prefix（随平台 perl 安装前缀
而异，package() 通过遍历定位 IO/Multiplex.pm，不依赖固定路径）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class PerlIoMultiplexConan(ConanFile):
    name = "perl-io-multiplex"
    version = "1.16"
    description = "IO::Multiplex — Manage multiple IO streams with a single callback"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/IO::Multiplex"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    # 纯 Perl 模块：Conan 无 perl 原生 package_type，沿用知识库 perl-uri
    # 先例的 python-require（无 C/C++ 二进制产物、无 commands.json）
    package_type = "python-require"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 鸿蒙平台预装 perl 标准路径（与知识库 perl-uri 先例一致）
        perl = "/data/service/hnp/bin/perl"
        self.run(f'{perl} Makefile.PL', cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)
        # R51：上游测试在 conan create 内真实运行（t/*.t，4 文件 32 断言）
        self.run("make test", cwd=self.source_folder)
        staging = os.path.join(self.build_folder, "perl-stage")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "perl-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"perl staging missing: {staging}")
        for root, _dirs, files in os.walk(staging):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, staging)
                dst = os.path.join(self.package_folder, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        # locate site_perl root that contains IO/Multiplex.pm
        # (install prefix varies by perl build — walk; site = parent of IO/)
        site = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "Multiplex.pm" in files and os.path.basename(root) == "IO":
                site = os.path.dirname(root)
                break
        if not site:
            raise ConanException("IO/Multiplex.pm not found in package")

    def package_info(self):
        site = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "Multiplex.pm" in files and os.path.basename(root) == "IO":
                site = os.path.dirname(root)
                break
        if site:
            # 注入消费者 PERL5LIB，下游 perl 脚本可直接 use IO::Multiplex
            self.output.info(f"PERL5LIB={site}")
            self.env_info.PERL5LIB = site

