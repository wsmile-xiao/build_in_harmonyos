#!/usr/bin/env python3
"""Conan recipe for perl-rt-extension-commandbymail 3.02 (RT::Extension::CommandByMail).

RT4 mail command extension - pure Perl module using ExtUtils::MakeMaker (EUMM).
The original Makefile.PL uses Module::Install + RTx() which requires RT to be
installed at configure time.  This recipe replaces it with a standard EUMM
Makefile.PL so the .pm files can be packaged without RT being present.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, patch as conan_patch
from conan.tools.layout import basic_layout


class PerlRtExtensionCommandByMailConan(ConanFile):
    name = "perl-rt-extension-commandbymail"
    version = "3.02"
    description = "RT4 mail command extension (RT::Extension::CommandByMail)"
    license = "GPL-2.0-or-later"
    homepage = "https://metacpan.org/release/RT-Extension-CommandByMail"
    url = "https://github.com/bestpractical/rt-extension-commandbymail"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Manually export patches directory (belt-and-suspenders for patch discovery)
        copy(self, "*.patch",
             src=os.path.join(self.recipe_folder, "patches"),
             dst=os.path.join(self.export_folder, "patches"))

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Check if patch was applied; if not, apply manually or write inline
        makefile_pl = os.path.join(src, "Makefile.PL")
        with open(makefile_pl) as f:
            content = f.read()
        if "Module::Install" in content:
            # Patch wasn't applied by apply_conandata_patches, try manual patch
            patch_path = os.path.join(self.export_sources_folder, "patches", "0001-Makefile.PL.patch")
            if os.path.isfile(patch_path):
                conan_patch(self, patch_path, base_path=src)
            else:
                # Fallback: write EUMM Makefile.PL inline
                eumm = r"""use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME          => 'RT::Extension::CommandByMail',
    DISTNAME      => 'RT-Extension-CommandByMail',
    VERSION       => '3.02',
    ABSTRACT      => 'Change ticket metadata via email',
    AUTHOR        => 'Best Practical Solutions, LLC <modules@bestpractical.com>',
    LICENSE       => 'gpl',
    INSTALLDIRS   => 'site',
    PREREQ_PM     => {
        'perl' => '5.10.1',
    },
    BUILD_REQUIRES => {
        'Test::More' => 0,
        'IPC::Open2' => 0,
    },
    clean         => { FILES => 'RT-Extension-CommandByMail-*' },
);
"""
                with open(makefile_pl, "w") as f:
                    f.write(eumm)
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=src)
        self.run("make -j1", cwd=src)

    def package(self):
        # Copy .pm files from blib/lib (built during make) into package
        src = self.source_folder
        copy(self, "*.pm",
             src=os.path.join(src, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
