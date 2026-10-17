#!/usr/bin/env python3
"""Conan recipe for perl-package-deprecationmanager 0.18-r1 (Package::DeprecationManager CPAN module).

This is a pure-Perl module built with ExtUtils::MakeMaker (Makefile.PL).
Build steps: perl Makefile.PL -> make -> make install

All runtime dependencies are vendored and installed to package lib/perl5/.
R36 exception: perl-package-stash/0.40-r1 and perl-params-util/1.102 are
published to ohpcd but their package_info() does not properly propagate
PERL5LIB to consumers in test_package context. Once fixed, replace
vendored sources with self.requires().
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlPackageDeprecationManagerConan(ConanFile):
    name = "perl-package-deprecationmanager"
    version = "0.18-r1"
    description = "Manage deprecation warnings for your distribution (Package::DeprecationManager CPAN module)"
    license = "artistic_2"
    homepage = "https://metacpan.org/dist/Package-DeprecationManager"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."

    def source(self):
        # Download Package::DeprecationManager (extracted to source root)
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download vendored dependencies
        for dep_name, dep_data in self.conan_data.get("dep_sources", {}).items():
            get(self, **dep_data, strip_root=True,
                destination=os.path.join(self.source_folder, dep_name))

    def build(self):
        apply_conandata_patches(self)

        pkg_lib = os.path.join(self.package_folder, "lib", "perl5")

        # Install vendored Perl dependencies in topological order.
        # Module::Implementation depends on Module::Runtime and Try::Tiny.
        # Package::Stash depends on Module::Implementation.
        for dep_name in ["Module-Runtime", "Try-Tiny", "Module-Implementation",
                         "Package-Stash", "Sub-Install"]:
            dep_dir = os.path.join(self.source_folder, dep_name)
            if os.path.isdir(dep_dir):
                self.run(
                    'PERL5LIB="{}" perl Makefile.PL --pureperl-only INSTALL_BASE={}'.format(
                        pkg_lib, self.package_folder),
                    cwd=dep_dir)
                self.run('PERL5LIB="{}" make PUREPERL_ONLY=1'.format(pkg_lib),
                         cwd=dep_dir)
                self.run('PERL5LIB="{}" make install PUREPERL_ONLY=1'.format(pkg_lib),
                         cwd=dep_dir)

        # Create pure-Perl Params::Util stub (XS version blocked by OHOS ELF signing).
        # Provides _CALLABLE, _SCALAR0, _HASHLIKE, _ARRAYLIKE used by DeprecationManager.
        params_dir = os.path.join(pkg_lib, "Params")
        os.makedirs(params_dir, exist_ok=True)
        with open(os.path.join(params_dir, "Util.pm"), "w") as f:
            f.write("""package Params::Util;
use strict;
use warnings;
use Exporter qw(import);
our @EXPORT_OK = qw(_CALLABLE _SCALAR0 _HASH0 _ARRAY0 _HASHLIKE _ARRAYLIKE);
our $VERSION = '1.102';
sub _CALLABLE  { ref $_[0] eq 'CODE' ? $_[0] : undef }
sub _SCALAR0   { ref $_[0] eq 'SCALAR' ? $_[0] : undef }
sub _HASH0     { (ref $_[0] eq 'HASH' and keys %{$_[0]}) ? $_[0] : undef }
sub _ARRAY0    { (ref $_[0] eq 'ARRAY' and @{$_[0]}) ? $_[0] : undef }
sub _HASHLIKE  { ref $_[0] eq 'HASH' ? $_[0] : undef }
sub _ARRAYLIKE { ref $_[0] eq 'ARRAY' ? $_[0] : undef }
1;
""")

        # Build Package::DeprecationManager (all deps installed in pkg_lib)
        self.run('PERL5LIB="{}" perl Makefile.PL INSTALL_BASE={}'.format(
            pkg_lib, self.package_folder))
        self.run('PERL5LIB="{}" make'.format(pkg_lib))

    def package(self):
        pkg_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.run('PERL5LIB="{}" make install'.format(pkg_lib))

    def package_info(self):
        # Perl module: expose lib path for consumers
        perl5_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl5_lib)
