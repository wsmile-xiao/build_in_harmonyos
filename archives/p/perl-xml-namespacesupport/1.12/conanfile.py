#!/usr/bin/env python3
"""Conan recipe for perl-xml-namespacesupport 1.12 — XML::NamespaceSupport
(pure-Perl, CPAN source).

XML::LibXML 的运行时依赖（use XML::SAX::Exception 链）——按 W0/R36
先发布本依赖。pure-Perl：perl Makefile.PL → make → make install DESTDIR。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlXmlNamespaceSupportConan(ConanFile):
    name = "perl-xml-namespacesupport"
    version = "1.12"
    description = "XML::NamespaceSupport — simple SAX2 namespace support"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/XML::NamespaceSupport"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        perl = "/data/service/hnp/bin/perl"
        self.run(f'{perl} Makefile.PL', cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)
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
        # 定位 XML/NamespaceSupport.pm 确认打包
        found = False
        for root, _dirs, files in os.walk(self.package_folder):
            if "NamespaceSupport.pm" in files:
                found = True
                break
        if not found:
            raise ConanException("XML/NamespaceSupport.pm not found in package")

    def package_info(self):
        for root, _dirs, files in os.walk(self.package_folder):
            if "NamespaceSupport.pm" in files:
                site = os.path.dirname(os.path.dirname(root))  # .../lib 层
                self.output.info(f"PERL5LIB={site}")
                return
