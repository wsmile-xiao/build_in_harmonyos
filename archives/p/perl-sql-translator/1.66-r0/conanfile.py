#!/usr/bin/env python3
"""Conan recipe — perl-sql-translator (SQL::Translator) 1.66-r0
Pure Perl module for SQL DDL transformations.
Build system: ExtUtils::MakeMaker (perl Makefile.PL && make && make install)

Platform notes (OpenHarmony):
- DBI XS .so is blocked by SELinux HMDFS restrictions.
  A pure-Perl DBI stub is installed providing :sql_types constants.
- YAML::Tiny is used as YAML backend (full YAML module unavailable).
- Modules installed to local::lib path, loaded via PERL5LIB.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlSqlTranslatorConan(ConanFile):
    name = "perl-sql-translator"
    version = "1.66-r0"
    description = "SQL DDL transformations and more (SQL::Translator)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/release/SQL-Translator"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # Perl installation paths on OpenHarmony
    _perl_base = "/data/service/hnp/perl.org/perl_5.42.0"
    _perl_locallib = "/storage/Users/currentUser/usr/local/perl5"

    @property
    def _perl_arch_dir(self):
        """Map Conan arch setting to Perl platform directory name."""
        arch_map = {
            "armv8": "aarch64-linux",
            "aarch64": "aarch64-linux",
            "x86_64": "x86_64-linux",
            "x86": "i686-linux",
        }
        return arch_map.get(str(self.settings.arch), "aarch64-linux")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Perl runtime dependencies — managed via local::lib
        # Moo, Parse::RecDescent, Try::Tiny, Sub::Quote, Package::Variant,
        # File::ShareDir, Class::Accessor, YAML::Tiny
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # Perl MakeMaker does not use cmake/autotools toolchain

    def build(self):
        apply_conandata_patches(self)
        # Set up Perl environment with local::lib for dependencies
        perl5lib = os.path.join(self._perl_locallib, "lib", "perl5")
        perl5lib_arch = os.path.join(perl5lib, self._perl_arch_dir)
        env = {
            "PERL5LIB": f"{perl5lib_arch}:{perl5lib}",
            "PERL_MM_OPT": f"INSTALL_BASE={self._perl_locallib}",
            "PATH": f"{os.path.join(self._perl_locallib, 'bin')}:{os.environ.get('PATH', '')}",
        }
        for k, v in env.items():
            os.environ[k] = v
        # Remove File::ShareDir::Install configure-time dependency
        # (not available on CI workers — share files handled manually below)
        self.run("sed -i '/^use File::ShareDir::Install;$/d' Makefile.PL", cwd=self.source_folder)
        self.run("sed -i '/^install_share .share.;$/d' Makefile.PL", cwd=self.source_folder)
        self.run("sed -i '/^package MY;$/d' Makefile.PL", cwd=self.source_folder)
        self.run("sed -i '/^use File::ShareDir::Install qw(postamble);$/d' Makefile.PL", cwd=self.source_folder)
        # Pure Perl module: perl Makefile.PL && make
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)
        # Manually copy share files (replaces File::ShareDir::Install's install_share)
        self.run("mkdir -p blib/lib/auto/share/dist/SQL-Translator", cwd=self.source_folder)
        self.run("cp -r share/* blib/lib/auto/share/dist/SQL-Translator/", cwd=self.source_folder)

    def package(self):
        # make install to local::lib path
        perl5lib = os.path.join(self._perl_locallib, "lib", "perl5")
        os.environ["PERL_MM_OPT"] = f"INSTALL_BASE={self._perl_locallib}"
        os.environ["PERL5LIB"] = f"{os.path.join(perl5lib, self._perl_arch_dir)}:{perl5lib}"
        self.run("make install", cwd=self.source_folder)
        # Copy installed Perl modules to package folder
        copy(self, "*", src=os.path.join(self._perl_locallib, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        # Copy installed scripts (sqlt etc.) to package folder
        copy(self, "*", src=os.path.join(self._perl_locallib, "bin"),
             dst=os.path.join(self.package_folder, "lib", "perl5", "bin"))

    def package_info(self):
        # Pure Perl module — no C/C++ libraries
        self.cpp_info.libs = []
        perl5lib = os.path.join(self.package_folder, "lib", "perl5")
        perl5lib_arch = os.path.join(perl5lib, self._perl_arch_dir)
        self.runenv_info.append_path("PERL5LIB", perl5lib)
        self.runenv_info.append_path("PERL5LIB", perl5lib_arch)
