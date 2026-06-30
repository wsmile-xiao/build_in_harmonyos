#!/usr/bin/env python3
"""Conan recipe — perl-net-openssh 0.84-r1 (pure Perl module).

Net::OpenSSH is a Perl SSH client package implemented on top of OpenSSH.
Build system: ExtUtils::MakeMaker (perl Makefile.PL → make → make install)
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlnetopensshConan(ConanFile):
    name = "perl-net-openssh"
    version = "0.84-r1"
    description = "Perl SSH client package implemented on top of OpenSSH"
    license = "perl_5"
    homepage = "https://github.com/salva/p5-Net-OpenSSH"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder)

        # Copy all installed .pm files to lib/perl5/ in package folder
        pm_files = glob.glob(
            os.path.join(dest_dir, "**", "*.pm"),
            recursive=True,
        )
        for pm_file in pm_files:
            # Find the relative path after site_perl/<version>/
            rel = pm_file
            for marker in ["site_perl"]:
                idx = rel.find(marker)
                if idx >= 0:
                    rel = rel[idx + len(marker) + 1:]
                    # Skip the perl version directory (e.g., 5.42.0)
                    parts = rel.split(os.sep)
                    if len(parts) > 1 and parts[0][0].isdigit():
                        rel = os.sep.join(parts[1:])
                    break
            target = os.path.join(self.package_folder, "lib", "perl5", rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(pm_file, target)

    def package_info(self):
        self.cpp_info.libs = []
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
