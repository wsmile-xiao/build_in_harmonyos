"""Conan recipe for Safe::Isa — pure Perl EUMM module.

Safe::Isa provides safe isa/can/does calls on things that may not be objects.
Build system: ExtUtils::MakeMaker (perl Makefile.PL + make).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlsafeisaConan(ConanFile):
    name = "perl-safe-isa"
    version = "1.000010"
    description = "Call isa, can, does and DOES safely on things that may not be objects"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Safe-Isa"
    url = ""  # CI fills this
    topics = "perl", "cpan", "safe-isa"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Generate Makefile via ExtUtils::MakeMaker
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=src)
        # Build the module (creates blib/lib structure)
        self.run("make -j1", cwd=src)

    def package(self):
        src = self.source_folder
        # For pure Perl modules, copy .pm files from source lib/ to package lib/perl5/
        copy(self, "*.pm",
             src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib", "perl5"),
             keep_path=True)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]

        # Set PERL5LIB for consumers
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
