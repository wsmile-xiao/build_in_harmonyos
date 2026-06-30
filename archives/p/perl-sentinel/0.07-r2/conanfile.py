#!/usr/bin/env python3
"""Conan recipe for perl-sentinel (Sentinel XS module).

Build system: Perl Makefile.PL + ExtUtils::MakeMaker
This is a Perl XS module that produces a shared library (.so) loaded by Perl's XSLoader.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlSentinelConan(ConanFile):
    name = "perl-sentinel"
    version = "0.07-r2"
    description = "create lightweight SCALARs with get/set callbacks"
    license = "perl"
    homepage = "https://metacpan.org/dist/Sentinel"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # Use source folder as build folder (no subdirectory)
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Create Makefile.PL (Module::Build not available, use ExtUtils::MakeMaker)
        makefile_pl = (
            "use 5.014;\n"
            "use strict;\n"
            "use warnings;\n"
            "use ExtUtils::MakeMaker;\n\n"
            "WriteMakefile(\n"
            "    NAME         => 'Sentinel',\n"
            "    VERSION_FROM => 'lib/Sentinel.pm',\n"
            "    LICENSE      => 'perl',\n"
            "    ABSTRACT     => 'create lightweight SCALARs with get/set callbacks',\n"
            "    AUTHOR       => 'Paul Evans <leonerd@leonerd.org.uk>',\n"
            "    PREREQ_PM    => { 'perl' => '5.014' },\n"
            "    TEST_REQUIRES => { 'Test2::V0' => '0.000148' },\n"
            "    XS           => { 'Sentinel.xs' => 'Sentinel.c' },\n"
            "    C            => [ 'Sentinel.c' ],\n"
            "    clean        => { FILES => 'Sentinel.c Sentinel.o' },\n"
            ");\n"
        )
        makefile_path = os.path.join(src, "Makefile.PL")
        with open(makefile_path, "w") as f:
            f.write(makefile_pl)

        # Symlink XS file to root for correct compilation
        xs_link = os.path.join(src, "Sentinel.xs")
        if not os.path.exists(xs_link):
            os.symlink("lib/Sentinel.xs", xs_link)

        # Generate Makefile and build
        self.run("perl Makefile.PL", cwd=src)
        self.run("make", cwd=src)

    def package(self):
        src = self.source_folder
        destdir = os.path.join(self.package_folder, "res")
        self.run(f"make install DESTDIR={destdir}", cwd=src)
        # Also copy .so to standard lib/ for G4 artifact detection
        from conan.tools.files import copy
        so_dir = os.path.join(src, "blib", "arch", "auto", "Sentinel")
        if os.path.isdir(so_dir):
            copy(self, "Sentinel.so", so_dir, os.path.join(self.package_folder, "lib"))
        # Copy .pm to lib/ for easy access
        pm_dir = os.path.join(src, "lib")
        if os.path.isdir(pm_dir):
            copy(self, "Sentinel.pm", pm_dir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Perl XS module: no C++ libraries to link
        self.cpp_info.libs = []
        # Set PERL5LIB so Perl can find the module
        if self.settings.os in ("Linux", "OHOS"):
            perl_site_arch = os.path.join(
                self.package_folder, "res", "data", "service", "hnp",
                "perl.org", "perl_5.42.0", "lib", "site_perl", "5.42.0",
                "aarch64-linux"
            )
            perl_site_lib = os.path.join(
                self.package_folder, "res", "data", "service", "hnp",
                "perl.org", "perl_5.42.0", "lib", "site_perl", "5.42.0"
            )
            self.runenv_info.append_path("PERL5LIB", perl_site_arch)
            self.runenv_info.append_path("PERL5LIB", perl_site_lib)
