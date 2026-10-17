#!/usr/bin/env python3
"""Conan recipe for perl-xml-parser 2.59 — XML::Parser (Expat XS binding).

XS module binding libexpat. Makefile.PL (ExtUtils::MakeMaker) build with
EXPATLIBPATH/EXPATINCPATH env injected from the expat dependency.
Requires: perl/5.42.2 + expat/2.8.2.1 (both published to ohpcd).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlXmlParserConan(ConanFile):
    name = "perl-xml-parser"
    version = "2.59"
    description = "XML::Parser — Perl interface to the expat XML parser"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/XML-Parser"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "unknown"

    # File::ShareDir::Install is a build-time dep of XML-Parser's Makefile.PL
    # (not published to ohpcd) — bundle it so build() can -I it.
    exports = ["test_package/File/ShareDir/Install.pm",
               "test_package/File/ShareDir.pm",
               "test_package/Class/Inspector.pm"]

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
        # The conan perl package lacks Config.pm / CORE headers (its @INC
        # paths are un-prefixed "//lib/perl5/..."), so XS compilation fails
        # with it. Use the FULL system perl (usr/local — Config/CORE intact)
        # for the XS build, same pattern as unicorn's python3 pinning.
        perl = "/storage/Users/currentUser/usr/local/bin/perl"
        if not os.path.isfile(perl):
            perl = "perl"
        expat = self.dependencies["expat"].package_folder
        # XML-Parser's Makefile.PL needs File::ShareDir::Install (build-time
        # dep, not in ohpcd) — bundle it in test_package and -I it.
        tp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "test_package")
        env = (
            f'EXPATLIBPATH="{expat}/lib" '
            f'EXPATINCPATH="{expat}/include" '
            f'LD_LIBRARY_PATH="{expat}/lib"'
        )
        # Override PERL5LIB so the system perl's @INC = our bundled
        # File::ShareDir::Install + system site_perl (NOT conan perl's XS
        # paths, which would cause "Cwd.c: perl binaries are mismatched").
        sys_site = "/storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.2"
        clean = (
            f'PERL5LIB="{tp}:{sys_site}" '
            f'LD_LIBRARY_PATH="{expat}/lib" '
            f'EXPATLIBPATH="{expat}/lib" EXPATINCPATH="{expat}/include"'
        )
        self.run(
            f'{clean} {perl} -I"{tp}" Makefile.PL INSTALLDIRS=site '
            f'PREFIX={self.package_folder}',
            cwd=self.source_folder,
        )
        self.run(f'{clean} make -j1', cwd=self.source_folder)
        self.run(f'{clean} make install', cwd=self.source_folder)

    def package(self):
        # CI's conan perl installs under lib/site_perl/<ver>/<arch>/ while
        # the local system perl uses lib/perl5/site_perl/... — find Expat.pm
        # anywhere under the package folder.
        found = None
        for root, _, files in os.walk(self.package_folder):
            if "Expat.pm" in files and root.endswith(os.path.join("XML", "Parser")):
                found = root
                break
        if not found:
            raise ConanException(
                "XML/Parser/Expat.pm not installed under "
                f"{self.package_folder}")

    def package_info(self):
        self.output.info("PERL5LIB=<package>/lib(perl5)/site_perl")
