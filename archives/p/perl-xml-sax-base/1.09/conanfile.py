#!/usr/bin/env python3
"""Conan recipe for perl-xml-sax-base 1.09 — XML::SAX::Base module
(pure-Perl, CPAN source, zero runtime dependencies).

Pure-Perl module: build via perl Makefile.PL → make → make install
DESTDIR into the conan package folder; consumers add site/lib to PERL5LIB.
perl path uses /data/service/hnp/bin/perl (CI-accessible — the local
usr/local absolute path is NOT reachable in CI workers, Error 127).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlXmlSaxBaseConan(ConanFile):
    name = "perl-xml-sax-base"
    version = "1.09"
    description = "XML::SAX::Base — SAX2 Driver base class"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/XML::SAX::Base"
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
        # locate XML/SAX/Base.pm (install prefix varies by perl build — walk)
        found = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "Base.pm" in files and os.path.basename(root) == "SAX":
                found = root
                break
        if not found:
            raise ConanException("XML/SAX/Base.pm not found in package")

    def package_info(self):
        # expose the site-perl root (parent of XML/) as PERL5LIB
        site = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "Base.pm" in files and os.path.basename(root) == "SAX":
                # root = .../XML/SAX → site-perl root = dirname(dirname(root))
                site = os.path.dirname(os.path.dirname(root))
                break
        if site:
            self.output.info(f"PERL5LIB={site}")
