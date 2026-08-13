#!/usr/bin/env python3
"""Conan recipe — perl-socket (Socket XS module) 2.040-r0.

Perl XS module using Makefile.PL + ExtUtils::MakeMaker.
Socket is a Perl core module providing network constants and functions.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlsocketConan(ConanFile):
    name = "perl-socket"
    version = "2.040-r0"
    description = "Socket - network constants and functions (Perl XS module)"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/Socket"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl XS module: use Makefile.PL + ExtUtils::MakeMaker
        # R1: minimal parameters, just use defaults
        self.run("perl Makefile.PL", cwd=self.source_folder, env="conanbuild")
        self.run("make", cwd=self.source_folder, env="conanbuild")

    def package(self):
        src = self.source_folder
        # Copy built artifacts to standard Conan package layout
        # Socket.so (XS shared library) -> lib/auto/Socket/
        so_src = os.path.join(src, "blib", "arch", "auto", "Socket", "Socket.so")
        so_dst = os.path.join(self.package_folder, "lib", "auto", "Socket")
        os.makedirs(so_dst, exist_ok=True)
        if not os.path.exists(so_src):
            raise ConanException(f"Socket.so not found at {so_src} — build may have failed")
        shutil.copy2(so_src, os.path.join(so_dst, "Socket.so"))
        # Socket.pm (Perl module) -> lib/
        pm_src = os.path.join(src, "blib", "lib", "Socket.pm")
        pm_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(pm_dst, exist_ok=True)
        if not os.path.exists(pm_src):
            raise ConanException(f"Socket.pm not found at {pm_src} — build may have failed")
        shutil.copy2(pm_src, os.path.join(pm_dst, "Socket.pm"))

    def package_info(self):
        # Perl XS module: no C library to link against
        # The .so is loaded dynamically by Perl's DynaLoader/XSLoader
        self.cpp_info.libs = []

        # Set PERL5LIB so Perl can find the installed module
        lib_dir = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", lib_dir)
