#!/usr/bin/env python3
"""Conan recipe — Perl module Net::Jabber (perl Makefile.PL build).

Net::Jabber is a pure Perl module providing access to the Jabber protocol.
Build system: perl Makefile.PL && make && make install

Dependencies (Perl-level, not Conan-managed):
- Net::XMPP >= 1.0 (installed via CPAN)
- XML::Stream >= 1.0 (installed via CPAN)
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlNetJabberConan(ConanFile):
    name = "perl-net-jabber"
    version = "2.0-r0"
    description = "Access the Jabber protocol with Perl"
    license = "LGPL-2.1"
    homepage = "https://metacpan.org/pod/Net::Jabber"
    url = ""  # CI fills this

    # Pure Perl module — settings needed for profile compatibility
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Perl module dependencies are managed at Perl level (CPAN)
        # No Conan-level dependencies for pure Perl modules
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder)

        # Find all installed .pm files and copy to lib/perl5/ in package folder
        pm_files = glob.glob(
            os.path.join(dest_dir, "**", "*.pm"),
            recursive=True,
        )
        for pm_file in pm_files:
            # Extract the path relative to the site_perl/ or perl5/ directory
            rel = os.path.relpath(pm_file, dest_dir)
            # Find site_perl/ in the path and extract from there
            for prefix in ["site_perl/", "perl5/"]:
                idx = rel.find(prefix)
                if idx >= 0:
                    rel = rel[idx + len(prefix):]
                    break
            # Also strip any version-specific path components like 5.42.0/
            if rel.startswith("5.") or rel.startswith("aarch64-linux/"):
                parts = rel.split(os.sep)
                # Skip version dirs and arch dirs
                while parts and (parts[0].startswith("5.") or parts[0] == "aarch64-linux"):
                    parts.pop(0)
                rel = os.sep.join(parts)
            target = os.path.join(self.package_folder, "lib", "perl5", rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(pm_file, target)

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
