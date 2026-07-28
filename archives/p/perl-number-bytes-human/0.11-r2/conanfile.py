#!/usr/bin/env python3
"""Conan recipe — perl-number-bytes-human (Number::Bytes::Human) 0.11-r2

Pure Perl module: Convert byte count to human readable format.
Build system: perl Makefile.PL + make + make install
No C/XS compilation, no external dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnumberbyteshumanConan(ConanFile):
    name = "perl-number-bytes-human"
    version = "0.11-r2"
    description = "Convert byte count to human readable format (Number::Bytes::Human)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Number-Bytes-Human"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        # Pure Perl module — no arch/compiler-dependent output
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure Perl module — no Conan dependencies
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl: perl Makefile.PL && make
        install_base = os.path.join(self.build_folder, "_perl_install")
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"')
        self.run("make -j1")

    def package(self):
        # Install to the build-local INSTALL_BASE, then copy to standard dirs
        self.run("make install")
        install_base = os.path.join(self.build_folder, "_perl_install")
        src_lib = os.path.join(install_base, "lib", "perl5")
        if os.path.exists(src_lib):
            copy(self, "*.pm", src_lib, os.path.join(self.package_folder, "lib"))
            copy(self, "*.pod", src_lib, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no C libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Perl modules are in lib/ — set PERL5LIB for consumers
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
