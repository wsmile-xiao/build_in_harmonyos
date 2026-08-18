#!/usr/bin/env python3
"""Conan recipe for perl-spreadsheet-xlsx 0.18

Perl extension for reading MS Excel 2007 files (Spreadsheet::XLSX).
Pure Perl module — no C compilation required.
Build system: ExtUtils::MakeMaker (perl Makefile.PL + make).

References:
  - R1:  parameter minimization (INSTALL_BASE=/ only)
  - R27: dependencies use @ohpcd/stable
  - R28: test_package/ present
  - R32: settings.os check uses in ("Linux", "OHOS")
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlSpreadsheetXlsxConan(ConanFile):
    name = "perl-spreadsheet-xlsx"
    version = "0.18"
    description = "Perl extension for reading MS Excel 2007 files (Spreadsheet::XLSX)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Spreadsheet-XLSX"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime deps: Archive::Zip >= 1.18, Spreadsheet::ParseExcel
        # These are Perl modules resolved at runtime via PERL5LIB, not Conan deps
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: Platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL + ExtUtils::MakeMaker
        # INSTALL_BASE=/ makes files install to $DESTDIR/lib/perl5/
        self.run("perl Makefile.PL INSTALL_BASE=/")
        # Use -j1 for safety on HarmonyOS
        self.run("make -j1")

    def package(self):
        # Install to staging directory with DESTDIR
        staging = os.path.join(self.build_folder, "staging")
        self.run(f"make install DESTDIR={staging}")
        # Copy lib/ subtree to package folder
        src_lib = os.path.join(staging, "lib")
        if os.path.exists(src_lib):
            copy(self, "*", src_lib, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module: no C libraries to link against
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.includedirs = []
        # Set PERL5LIB so consumers can find the module
        # Files are under lib/perl5/<arch>/ and lib/perl5/
        perl_dirs = glob.glob(
            os.path.join(self.package_folder, "lib", "perl5", "*")
        )
        for perl_dir in perl_dirs:
            if os.path.isdir(perl_dir):
                self.runenv_info.append_path("PERL5LIB", perl_dir)
        # Also add lib/perl5 base for pure-Perl modules
        base_perl = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(base_perl):
            self.runenv_info.append_path("PERL5LIB", base_perl)
