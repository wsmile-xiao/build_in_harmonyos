#!/usr/bin/env python3
"""Conan recipe — HTTP::Parser::XS Perl XS module.

Build system: Perl Module::Install (Makefile.PL + make)
This is a Perl XS module that compiles C sources (picohttpparser) into a
shared library loaded by Perl's XSLoader/DynaLoader.

Adaptations for OHOS:
- Perl XS modules need special linker flags: -nostartfiles -nodefaultlibs -lc
  to bypass missing CRT files (crtbeginS.o, crtendS.o) in OHOS sysroot
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlHttpParserXsConan(ConanFile):
    name = "perl-http-parser-xs"
    version = "0.17-r9"
    description = "A fast, primitive HTTP request/response parser Perl XS module"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/HTTP-Parser-XS"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Use absolute INSTALL_BASE pointing to staging dir in build folder
        install_base = os.path.join(self.build_folder, "lib", "perl5")

        # Step 1: Generate Makefile using Module::Install (Makefile.PL)
        # Perl 5.26+ removed '.' from @INC; Module::Install needs inc/ from cwd
        self.run(f'perl -I. Makefile.PL INSTALL_BASE="{install_base}"')

        # Step 2: Build with special linker flags for OHOS
        # OHOS sysroot lacks crtbeginS.o/crtendS.o — use -nostartfiles -nodefaultlibs -lc
        self.run('make -j1 OTHERLDFLAGS="-nostartfiles -nodefaultlibs -lc"')

        # Step 3: Install to staging dir (INSTALL_BASE is absolute)
        self.run("make install")

    def package(self):
        # Copy installed files from build staging to package folder
        copy(self, "*.so", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pm", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pod", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # This is a Perl XS module, not a C library
        # The .so is loaded by Perl's XSLoader at runtime
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")
        # MakeMaker installs modules under lib/perl5/$arch/ (e.g. aarch64-linux)
        arch_dirs = glob.glob(os.path.join(perl_lib, "*"))
        for d in arch_dirs:
            if os.path.isdir(d):
                self.runenv_info.append_path("PERL5LIB", d)
                self.output.info(f"PERL5LIB arch path: {d}")
                break
        self.cpp_info.includedirs = []
