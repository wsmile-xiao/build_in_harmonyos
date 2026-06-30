#!/usr/bin/env python3
"""Conan recipe for perl-rpc-xml 0.82 (RPC::XML — XML-RPC client/server).

Build system: Perl EUMM (ExtUtils::MakeMaker)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlRpcXmlConan(ConanFile):
    name = "perl-rpc-xml"
    version = "0.82"
    description = "Data, client and server classes for XML-RPC (RPC::XML)"
    license = "perl"  # Perl Artistic License 2.0
    homepage = "https://github.com/rjray/rpc-xml"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl EUMM build - run from source folder
        src = self.source_folder
        self.run(f'cd "{src}" && perl Makefile.PL INSTALLDIRS=site')
        self.run(f'cd "{src}" && make -j1')

    def package(self):
        src = self.source_folder
        # Install to DESTDIR staging
        destdir = os.path.join(self.build_folder, "destdir")
        os.makedirs(destdir, exist_ok=True)
        self.run(f'cd "{src}" && make install DESTDIR="{destdir}"')

        # Copy installed files to package
        # Perl installs to data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/
        # We flatten to lib/perl5/ so PERL5LIB=lib/perl5 works
        for root, dirs, files in os.walk(destdir):
            for f in files:
                src_file = os.path.join(root, f)
                rel = os.path.relpath(src_file, destdir)
                parts = rel.split(os.sep)

                # Skip .packlist and perllocal.pod
                if f in (".packlist", "perllocal.pod"):
                    continue

                if "site_perl" in parts:
                    # Find site_perl index, skip it and version dir (e.g. 5.42.0)
                    idx = parts.index("site_perl")
                    remaining = parts[idx + 1:]
                    # Skip version directory (starts with digit)
                    if remaining and remaining[0] and remaining[0][0].isdigit():
                        remaining = remaining[1:]
                    new_rel = os.path.join("lib", "perl5", *remaining)
                elif "bin" in parts:
                    idx = parts.index("bin")
                    new_rel = os.path.join("bin", *parts[idx + 1:])
                else:
                    continue

                dst_file = os.path.join(self.package_folder, new_rel)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]
        # Set PERL5LIB for consumers
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
