#!/usr/bin/env python3
"""Conan recipe for perl-html-parser 3.85 — HTML::Parser (XS, libexpat).

XS module (HTML::Parser) binding libexpat, pure-Perl HTML::Entities etc.
Build with the FULL system perl (conan perl package lacks Config.pm/CORE
headers — same pattern as perl-xml-parser). Deps on HTML::Tagset/URI/
HTTP::Headers exist in the system perl's site_perl.
Requires: perl/5.42.2 + expat/2.8.2.1 (published to ohpcd).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlHtmlParserConan(ConanFile):
    name = "perl-html-parser"
    version = "3.85"
    description = "HTML::Parser — HTML parser modules (HTML::Entities etc.)"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/HTML-Parser"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "unknown"

    requires = (
        "perl/5.42.2",
        "expat/2.8.2.1",
    )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # conan perl package lacks Config.pm/CORE headers → XS build with the
        # full system perl (perl-xml-parser same pattern). Deps (HTML::Tagset,
        # URI, HTTP::Headers) are in the system perl's site_perl.
        perl = "/storage/Users/currentUser/usr/local/bin/perl"
        if not os.path.isfile(perl):
            perl = "perl"
        expat = self.dependencies["expat"].package_folder
        sys_site = "/storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.2"
        clean = (
            f'PERL5LIB="{sys_site}" '
            f'LD_LIBRARY_PATH="{expat}/lib" '
            f'EXPATLIBPATH="{expat}/lib" EXPATINCPATH="{expat}/include"'
        )
        self.run(
            f'{clean} {perl} Makefile.PL INSTALLDIRS=site '
            f'PREFIX={self.package_folder}',
            cwd=self.source_folder,
        )
        self.run(f'{clean} make -j1', cwd=self.source_folder)
        self.run(f'{clean} make install', cwd=self.source_folder)

    def package(self):
        # CI's conan perl installs under lib/site_perl/<ver>/<arch>/ while
        # the local system perl uses lib/perl5/site_perl/... — find
        # HTML/Parser.pm anywhere under the package folder.
        found = None
        for root, _, files in os.walk(self.package_folder):
            if "Parser.pm" in files and root.endswith(os.path.join("HTML")):
                found = root
                break
        if not found:
            raise ConanException(
                "HTML/Parser.pm not installed under "
                f"{self.package_folder}")

    def package_info(self):
        self.output.info("PERL5LIB=<package>/lib(perl5)/site_perl")
