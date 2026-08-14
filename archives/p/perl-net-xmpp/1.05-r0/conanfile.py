#!/usr/bin/env python3
"""Conan recipe for perl-net-xmpp 1.05-r0 (pure Perl module).

Net::XMPP - XMPP Support Library
Build system: Perl Module::Build (via Makefile.PL compat wrapper).
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlNetXmppConan(ConanFile):
    name = "perl-net-xmpp"
    version = "1.05-r0"
    description = "XMPP Support Library"
    license = "LGPL-2.1-or-later"
    homepage = "https://metacpan.org/dist/Net-XMPP"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime dependencies (Perl modules available in system Perl)
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL + make
        # Makefile.PL patched to use ExtUtils::MakeMaker (Module::Build removed from Perl 5.42+)
        self.run("perl Makefile.PL", env="conanbuild")
        self.run("make", env="conanbuild")

    def package(self):
        # Install to a temporary DESTDIR, then copy .pm files to lib/perl5/
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run(f'make install DESTDIR="{dest_dir}"', env="conanbuild")

        # Find all installed .pm files and copy to lib/perl5/ in package folder
        pm_files = glob.glob(
            os.path.join(dest_dir, "**", "*.pm"),
            recursive=True,
        )
        for pm_file in pm_files:
            # Extract the path relative to the dest_dir
            rel = os.path.relpath(pm_file, dest_dir)
            # Find site_perl/ or perl5/ in the path and extract from there
            for prefix in ["site_perl/", "perl5/"]:
                idx = rel.find(prefix)
                if idx >= 0:
                    rel = rel[idx + len(prefix):]
                    break
            # Strip version-specific path components like 5.42.0/ or aarch64-linux/
            if rel.startswith("5.") or rel.startswith("aarch64-linux/"):
                parts = rel.split(os.sep)
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
