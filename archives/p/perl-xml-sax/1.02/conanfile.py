#!/usr/bin/env python3
"""Conan recipe for perl-xml-sax 1.02 — XML::SAX::Exception/Base 等
(pure-Perl, CPAN source, depends on XML::NamespaceSupport).

XML::LibXML 编译期依赖（use XML::SAX::Exception）——按 W0/R36 先发布。
pure-Perl：perl Makefile.PL → make → make install DESTDIR。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlXmlSaxConan(ConanFile):
    name = "perl-xml-sax"
    version = "1.02"
    description = "XML::SAX — Simple API for XML (SAX2) for perl"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/XML::SAX"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def requirements(self):
        # XML::SAX 依赖 XML::NamespaceSupport + XML::SAX::Base/Exception
        # （XML-SAX 1.02 Makefile.PL PREREQ_PM 声明 Base>=1.05；Exception 由
        #  perl-xml-sax-base 提供——编译期 use XML::SAX::Exception）
        self.requires("perl-xml-namespacesupport/1.12",
                      transitive_headers=True, transitive_libs=True)
        self.requires("perl-xml-sax-base/1.09",
                      transitive_headers=True, transitive_libs=True)

    def build(self):
        perl = "/data/service/hnp/bin/perl"
        # 注入依赖 PERL5LIB：perl Makefile.PL 时需能找到 XML::NamespaceSupport
        # 与 XML::SAX::Base/Exception
        dep_site = self._find_dep_site()
        base_site = self._find_base_site()
        sites = ":".join(x for x in (dep_site, base_site) if x)
        env = f"PERL5LIB={sites}" if sites else ""
        self.run(f'{env} {perl} Makefile.PL'.strip(), cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)
        staging = os.path.join(self.build_folder, "perl-stage")
        # install_sax_pureperl 钩子在 make install 内调用 perl 加载刚构建的
        # XML::SAX 自身——PERL5LIB 需含 blib/lib 与依赖 site（否则
        # "Can't locate XML/SAX.pm in @INC"，见 XML-SAX 1.02 实证）
        blib = os.path.join(self.source_folder, "blib", "lib")
        env_install = ":".join(x for x in (sites, blib) if x)
        self.run(
            f'make install DESTDIR="{staging}" PERL5LIB="{env_install}"',
            cwd=self.source_folder)

    def _find_base_site(self):
        # 在 perl-xml-sax-base 依赖包中定位 XML/SAX/Exception.pm 的 @INC 根
        for _ref, dep in self.dependencies.items():
            if dep.ref.name == "perl-xml-sax-base":
                for root, _dirs, files in os.walk(dep.package_folder):
                    if "Exception.pm" in files:
                        return os.path.dirname(os.path.dirname(os.path.dirname(root)))
        return ""

    def _find_dep_site(self):
        # 在依赖包中定位 XML/ 的父目录（@INC 根），无则返回 ""
        for _ref, dep in self.dependencies.items():
            for root, _dirs, files in os.walk(dep.package_folder):
                if "NamespaceSupport.pm" in files:
                    return os.path.dirname(os.path.dirname(root))
        return ""

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
        found = False
        for root, _dirs, files in os.walk(self.package_folder):
            if "Exception.pm" in files:
                found = True
                break
        if not found:
            raise ConanException("XML/SAX/Exception.pm not found in package")

    def package_info(self):
        for root, _dirs, files in os.walk(self.package_folder):
            if "Exception.pm" in files:
                site = os.path.dirname(os.path.dirname(os.path.dirname(root)))
                self.output.info(f"PERL5LIB={site}")
                return
