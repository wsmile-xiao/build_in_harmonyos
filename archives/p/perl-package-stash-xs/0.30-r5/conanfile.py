#!/usr/bin/env python3
"""Conan recipe — perl-package-stash-xs 0.30-r5 (Perl XS module)

Package::Stash::XS - Faster and more correct implementation of the Package::Stash API.
This is a Perl XS module (contains C code compiled to .so).

HarmonyOS adaptations (via patch):
- INC: add system header backup paths (sys/types.h, endian.h)
- dynamic_lib OTHERLDFLAGS: -nostartfiles -nodefaultlibs -L/system/lib64 -lc
  (HarmonyOS missing CRT files: crti.o, crtn.o, crtbeginS.o, crtendS.o)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlPackageStashXsConan(ConanFile):
    name = "perl-package-stash-xs"
    version = "0.30-r5"
    description = "Faster and more correct implementation of the Package::Stash API (XS)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Package-Stash-XS"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl XS module build: perl Makefile.PL && make
        # Patch already modifies Makefile.PL with HarmonyOS-specific INC and dynamic_lib flags
        home = os.environ.get("HOME", "/")
        perl_lib = f"{home}/usr/local/lib/site_perl/5.42.0:{home}/usr/local/lib/5.42.0"
        os.environ["PERL5LIB"] = perl_lib
        self.run(f"perl Makefile.PL PREFIX={home}/usr/local", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        # Perl XS module — not a C/C++ library, no cpp_info to expose
        pass
