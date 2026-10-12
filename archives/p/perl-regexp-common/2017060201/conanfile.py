#!/usr/bin/env python3
"""Conan recipe for perl-regexp-common 2017060201 (Regexp::Common).

CPAN distribution: Regexp-Common by Abigail.
Pure Perl module — no XS/C code, no CPAN runtime prerequisites beyond Perl
core (vars/strict/warnings/Config); requires Perl >= 5.10, provided by the
CI perl environment (hnp perl in PATH).

Build system: ExtUtils::MakeMaker (Makefile.PL), same pattern as the
published perl-regexp-common/2024080801 recipe.

Source URL and SHA256 are embedded in this recipe (no conandata.yml) so the
package never enters the CI conandata.yml pre-download path, which fails with
"BUILD_DIR: parameter not set" (see notes.md).
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

_source_url = (
    "https://www.cpan.org/modules/by-authors/id/A/AB/ABIGAIL/"
    "Regexp-Common-2017060201.tar.gz"
)
_source_sha256 = (
    "ee07853aee06f310e040b6bf1a0199a18d81896d3219b9b35c9630d0eb69089b"
)


class PerlRegexpCommonConan(ConanFile):
    name = "perl-regexp-common"
    version = "2017060201"
    description = "Regexp::Common - Provide commonly requested regular expressions (pure Perl module)"
    license = "mit"
    homepage = "https://metacpan.org/dist/Regexp-Common"
    url = ""  # CI fills this

    # CI L0 requires all four settings even for pure Perl modules
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # Same as perl-regexp-common/2024080801: `conan create` exports the
        # recipe to the Conan cache first, so source() extracts into the cache
        # build folder and never pollutes the recipe directory in Git.
        basic_layout(self)

    def generate(self):
        # Pure Perl module, no C/XS code — no toolchain needed
        pass

    def source(self):
        get(
            self,
            url=_source_url,
            sha256=_source_sha256,
            strip_root=True,
        )

    def build(self):
        # Pure Perl: generate the Makefile (TESTS glob t/*.t t/*/*.t is wired
        # into the generated Makefile for consumer-side test runs).
        # perl is not on the runner's default PATH on HarmonyOS PC devices;
        # fall back to the hnp perl install (same fallback as perl-cgi).
        perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
        self.run(f'"{perl}" Makefile.PL INSTALLDIRS=site', cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to staging, then copy Perl .pm files to lib/perl5/... at the
        # package root for G4 compatibility (same layout as 2024080801).
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)
        for pm_file in glob.glob(os.path.join(staging, "**", "*.pm"), recursive=True):
            rel = os.path.relpath(pm_file, staging)
            parts = rel.split(os.sep)
            if "site_perl" in parts:
                idx = parts.index("site_perl")
                target_rel = os.path.join("lib", "perl5", *parts[idx:])
            else:
                target_rel = os.path.join("lib", "perl5", rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pm_file),
                 src=os.path.dirname(pm_file), dst=os.path.dirname(target))

        share = os.path.join(self.package_folder, "share", self.name)
        # Upstream test tree + metadata for consumer-side TAP runs.
        copy(self, "t/*", src=self.source_folder, dst=share, keep_path=True)
        for meta in ("META.json", "META.yml", "Makefile.PL", "README", "Changes"):
            copy(self, meta, src=self.source_folder, dst=share)
        # Licenses.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for lic in ("COPYRIGHT", "COPYRIGHT.AL", "COPYRIGHT.AL2",
                    "COPYRIGHT.BSD", "COPYRIGHT.MIT"):
            copy(self, lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Pure Perl module — libraries are .pm files under lib/perl5.
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers — glob to find the actual site_perl path.
        for site_lib in glob.glob(
            os.path.join(self.package_folder, "lib", "perl5", "site_perl", "*")
        ):
            if os.path.isdir(site_lib):
                self.runenv_info.append_path("PERL5LIB", site_lib)
                self.buildenv_info.append_path("PERL5LIB", site_lib)
                break
