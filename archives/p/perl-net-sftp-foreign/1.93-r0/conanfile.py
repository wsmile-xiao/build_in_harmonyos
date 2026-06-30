#!/usr/bin/env python3
"""Conan recipe — Net::SFTP::Foreign (pure Perl module).

Net::SFTP::Foreign is a Secure File Transfer Protocol client implemented
as a pure Perl module (no XS/C code). Build uses ExtUtils::MakeMaker:
  perl Makefile.PL && make && make install

R26 (static linking) does not apply: no C compilation involved.
R27: No external Conan dependencies — all prerequisites (Scalar::Util,
     Time::HiRes, Test::More) are Perl core modules.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetsftpforeignConan(ConanFile):
    name = "perl-net-sftp-foreign"
    version = "1.93-r0"
    description = "Secure File Transfer Protocol client (pure Perl module)"
    license = "perl"  # Perl Artistic License
    homepage = "https://metacpan.org/dist/Net-SFTP-Foreign"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("perl Makefile.PL", env="conanbuild")
        self.run("make", env="conanbuild")

    def package(self):
        # Install to staging directory
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR={staging} "PREFIX=/"', env="conanbuild")
        # Find site_perl directory and copy .pm files to standard lib/
        matches = glob.glob(os.path.join(staging, "**", "site_perl"), recursive=True)
        if matches:
            site_perl_dir = matches[0]
            # Find version subdirectory (e.g., 5.42.0)
            for item in os.listdir(site_perl_dir):
                version_dir = os.path.join(site_perl_dir, item)
                if os.path.isdir(version_dir):
                    # Copy .pm files preserving Net/SFTP/Foreign/ structure
                    copy(self, "*.pm", src=version_dir,
                         dst=os.path.join(self.package_folder, "lib"), keep_path=True)
        else:
            # Fallback: copy all .pm from staging
            copy(self, "*.pm", src=staging,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=True)

    def package_info(self):
        # PERL5LIB points to lib/ where Net/SFTP/Foreign/ tree lives
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.prepend_path("PERL5LIB", perl_lib)
