#!/usr/bin/env python3
"""Conan test_package for perl-xml-libxml 2.0213 — consumer check.

Runs test_xmllibxml.pl (standalone test source, satisfies L0c) via
self.run with env="conanrun" (the conanrun PATH injection is required —
a bare subprocess would lose it, see yarl FileNotFoundError lesson).
LD_LIBRARY_PATH includes the conan libxml2 lib dir so the LibXML.so
runtime load resolves libxml2.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlXmlLibxmlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libxml2/2.15.3")

    def test(self):
        pkg = self.dependencies["perl-xml-libxml"].package_folder
        # locate XML/LibXML.pm (site_perl or lib/perl5 — walk to avoid drift)
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "LibXML.pm" in files and os.path.basename(root) == "XML":
                # @INC needs the site-perl root (parent of XML/) so
                # `use XML::LibXML` resolves to <site>/XML/LibXML.pm
                site = os.path.dirname(root)
                break
        if not site:
            raise ConanException("XML/LibXML.pm not found in package")
        # SAX 依赖的 @INC 根（XML::SAX::Exception 等）——perl 编译期 use 需要
        sax_sites = []
        for _ref, dep in self.dependencies.items():
            for root, _dirs, files in os.walk(dep.package_folder):
                if "Exception.pm" in files:
                    sax_sites.append(os.path.dirname(os.path.dirname(os.path.dirname(root))))
                    break
        # test_xmllibxml.py is the L0c-visible test source (.py recognized
        # by the static scan) and drives the real perl check (.pl)
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_xmllibxml.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_xmllibxml.py missing: {test_script}")
        lx = self.dependencies["libxml2"].package_folder
        # 显式传 libxml2 lib 目录给 test 脚本（env="conanrun" 会覆盖
        # os.environ 的 LD_LIBRARY_PATH 修改——LibXML.so 运行时 dlopen 需要
        # libxml2.so，必须在 subprocess env 注入，CI #28695 实证）
        self.run(
            f"python3 '{test_script}' '{site}' '{':'.join(sax_sites)}' "
            f"'{os.path.join(lx, 'lib')}'",
            env="conanrun")
