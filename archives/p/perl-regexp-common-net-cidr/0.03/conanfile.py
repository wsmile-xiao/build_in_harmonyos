#!/usr/bin/env python3
"""Conan recipe for perl-regexp-common-net-cidr 0.03 (Regexp::Common::net::CIDR).

Pure Perl module — provides patterns for CIDR blocks.
Build system: ExtUtils::MakeMaker (replacement Makefile.PL, avoiding Module::Install).
Requires: Regexp::Common (Conan dependency: perl-regexp-common/2024080801@ohpcd/stable).
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlRegexpCommonNetCidrConan(ConanFile):
    name = "perl-regexp-common-net-cidr"
    version = "0.03"
    description = "Regexp::Common::net::CIDR - Provide patterns for CIDR blocks (Pure Perl module)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Regexp-Common-net-CIDR"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("perl-regexp-common/2024080801@ohpcd/stable")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Pure Perl module, no C/XS code — no toolchain needed
        pass

    def _get_perl5lib(self):
        """Build PERL5LIB from Conan dependency + system Perl paths."""
        parts = []

        # Get Regexp::Common path from Conan dependency
        deps_pkg = self.dependencies["perl-regexp-common"]
        deps_folder = deps_pkg.package_folder
        for site_lib in glob.glob(os.path.join(deps_folder, "lib", "perl5", "site_perl", "*")):
            if os.path.isdir(site_lib):
                parts.append(site_lib)
                break

        # Add system Perl site_perl as fallback
        for sys_path in [
            "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0",
            "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0",
        ]:
            if os.path.isdir(sys_path):
                parts.append(sys_path)

        existing = os.environ.get("PERL5LIB", "")
        if existing:
            parts.append(existing)

        return ":".join(parts)

    def build(self):
        apply_conandata_patches(self)

        # Original source uses Module::Install (inc::Module::Install) which
        # triggers auto-install of missing dependencies during make, causing
        # build failures in isolated environments. Replace with a standard
        # ExtUtils::MakeMaker Makefile.PL.
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")
        makefile_pl_content = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME          => 'Regexp::Common::net::CIDR',
    VERSION_FROM  => 'lib/Regexp/Common/net/CIDR.pm',
    ABSTRACT_FROM => 'lib/Regexp/Common/net/CIDR.pm',
    AUTHOR        => 'Ruslan U. Zakirov <ruz@bestpractical.com>',
    LICENSE       => 'perl_5',
    PREREQ_PM     => {
        'Regexp::Common' => 0,
    },
    MIN_PERL_VERSION => '5.008',
    NO_MYMETA => 1,
);
"""
        with open(makefile_pl, "w") as f:
            f.write(makefile_pl_content)

        perl5lib = self._get_perl5lib()
        env_vars = [f"PERL5LIB={perl5lib}"]

        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder, env=env_vars)
        self.run("make -j1", cwd=self.source_folder, env=env_vars)

    def package(self):
        perl5lib = self._get_perl5lib()
        env_vars = [f"PERL5LIB={perl5lib}"]

        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder, env=env_vars)

        # Copy Perl .pm files to lib/perl5 at package root (consistent with perl-regexp-common)
        for pm_file in glob.glob(os.path.join(staging, "**", "*.pm"), recursive=True):
            rel = os.path.relpath(pm_file, staging)
            parts = rel.split(os.sep)
            if 'site_perl' in parts:
                idx = parts.index('site_perl')
                target_rel = os.path.join('lib', 'perl5', *parts[idx:])
            else:
                target_rel = os.path.join('lib', 'perl5', rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pm_file), src=os.path.dirname(pm_file), dst=os.path.dirname(target))

    def package_info(self):
        # Pure Perl module — libraries are .pm files in lib/perl5
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers — use glob to find the actual site_perl path
        for site_lib in glob.glob(os.path.join(self.package_folder, "lib", "perl5", "site_perl", "*")):
            if os.path.isdir(site_lib):
                self.runenv_info.append_path("PERL5LIB", site_lib)
                break
