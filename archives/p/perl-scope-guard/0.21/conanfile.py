#!/usr/bin/env python3
"""Conan recipe for perl-scope-guard 0.21 (Scope::Guard).

Pure Perl module - lexically-scoped resource management (RAII-style).
Build system: ExtUtils::MakeMaker (Makefile.PL).

参考 perl-dbd-pg 编译经验：纯 Perl 模块无需特殊链接参数，
直接 perl Makefile.PL && make，无 generate() 方法。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlScopeGuardConan(ConanFile):
    name = "perl-scope-guard"
    version = "0.21"
    description = "Scope::Guard - lexically-scoped resource management (pure Perl)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Scope-Guard"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "*.pm",
             src=os.path.join(self.source_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
