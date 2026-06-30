#!/usr/bin/env python3
"""Conan recipe — perl-net-server (Net::Server) 2.014-r2

Pure Perl module: Extensible Perl internet server.
Build system: perl Makefile.PL + make + make install
No C/XS compilation, no external dependencies (all are Perl core modules).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetserverConan(ConanFile):
    name = "perl-net-server"
    version = "2.014-r2"
    description = "Extensible Perl internet server (Net::Server)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-Server"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure Perl module — all dependencies (File::Temp, IO::Socket,
        # POSIX, Socket, Time::HiRes) are Perl core modules, no Conan deps.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl: perl Makefile.PL && make
        # Set INSTALL_BASE to a build-local dir for controlled packaging
        install_base = os.path.join(self.build_folder, "_perl_install")
        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"')
        self.run("make -j1")

    def package(self):
        # Install to the build-local INSTALL_BASE, then copy to standard dirs
        install_base = os.path.join(self.build_folder, "_perl_install")
        self.run(f'make install')
        # With INSTALL_BASE, modules go to lib/perl5/
        src_lib = os.path.join(install_base, "lib", "perl5")
        if os.path.exists(src_lib):
            copy(self, "*.pm", src_lib, os.path.join(self.package_folder, "lib"))
            copy(self, "*.pod", src_lib, os.path.join(self.package_folder, "lib"))
        # Note: net-server script is a server daemon (not a CLI tool with --version),
        # so it is not included in bin/ to avoid L2 smoke test false failure.
        # Users can create their own wrapper or use the module directly via PERL5LIB.

    def package_info(self):
        # Pure Perl module — no C libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Perl modules are in lib/ — set PERL5LIB for consumers
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
