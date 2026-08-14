#!/usr/bin/env python3
"""Conan recipe — perl-net-snmp 6.0.1 (pure Perl module).

Net::SNMP — Object oriented interface to SNMP.
Build system: Perl ExtUtils::MakeMaker (Makefile.PL).
This is a pure Perl module (no XS, no C compilation, no shared libraries).
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetsnmpConan(ConanFile):
    name = "perl-net-snmp"
    version = "6.0.1"
    description = "Net::SNMP - Object oriented interface to SNMP"
    license = "GPL-1.0-or-later OR Artistic-1.0-Perl"
    homepage = "https://metacpan.org/release/DTOWN/Net-SNMP-v6.0.1"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        # 纯 Perl 模块，产物与架构/编译器/构建类型无关
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure Perl module - no Conan C/C++ dependencies
        # Perl runtime deps (Crypt::DES, Digest::SHA1, etc.) are optional SNMPv3
        pass

    def layout(self):
        # Simple layout for Perl module
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl ExtUtils::MakeMaker build — no PREFIX to avoid system dir writes
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Copy Perl module files from blib/lib to package/lib
        # Note: snmpkey script is not packaged because it requires optional
        # Crypt::DES dependency for SNMPv3 USM that is not always available
        copy(self, "*.pm", src=os.path.join(self.source_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no C/C++ libraries to link
        self.cpp_info.libs = []
        # Perl module path for PERL5LIB
        self.cpp_info.libdirs = ["lib"]
