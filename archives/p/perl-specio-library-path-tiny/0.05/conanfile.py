#!/usr/bin/env python3
"""Conan recipe for perl-specio-library-path-tiny 0.05 (Specio::Library::Path::Tiny).

Pure Perl module — Path::Tiny types and coercions for Specio.
Build system: ExtUtils::MakeMaker (Makefile.PL).

References:
  - R1: parameters minimal (only --prefix equivalent via INSTALLDIRS)
  - R27: dependencies use @ohpcd/stable
  - R28: test_package/ present
  - R32: settings.os check uses in ("Linux", "OHOS")
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlSpecioLibraryPathTinyConan(ConanFile):
    name = "perl-specio-library-path-tiny"
    version = "0.05"
    description = "Path::Tiny types and coercions for Specio (Pure Perl module)"
    license = "Apache-2.0"
    homepage = "https://metacpan.org/dist/Specio-Library-Path-Tiny"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    # Specio 0.53 is available as a system Perl module (installed at
    # /storage/Users/currentUser/usr/local/lib/site_perl/5.42.0).
    # Not declared as a Conan dependency because perl-specio has not been
    # published to the Conan remote yet. PERL5LIB in _get_perl5lib() handles
    # the system Perl path resolution.

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Pure Perl module, no C/XS code — no toolchain needed
        pass

    def _get_perl5lib(self):
        """Build PERL5LIB from system Perl paths for runtime deps."""
        parts = []
        for sys_path in [
            "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0",
            "/storage/Users/currentUser/usr/local/lib/perl5",
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

        # R32: Platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        perl5lib = self._get_perl5lib()
        env_vars = [f"PERL5LIB={perl5lib}", "SPECIO_IMPLEMENTATION=PP"]

        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder, env=env_vars)
        self.run("make -j1", cwd=self.source_folder, env=env_vars)

    def package(self):
        perl5lib = self._get_perl5lib()
        env_vars = [f"PERL5LIB={perl5lib}", "SPECIO_IMPLEMENTATION=PP"]

        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder, env=env_vars)

        # Copy Perl .pm files to lib/perl5 at package root
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
        # Force PP backend for Specio (XS Clone cannot clone CODE refs on OHOS)
        self.runenv_info.define("SPECIO_IMPLEMENTATION", "PP")
        # Set PERL5LIB for consumers
        for site_lib in glob.glob(os.path.join(self.package_folder, "lib", "perl5", "site_perl", "*")):
            if os.path.isdir(site_lib):
                self.runenv_info.append_path("PERL5LIB", site_lib)
                break
