#!/usr/bin/env python3
"""Conan recipe — ExtUtils::Builder::Compiler Perl PurePerl module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a PurePerl module (no XS/C code) that provides a unified compiler
interface for Perl module developers.

Adaptations for OHOS:
- No source patches needed (PurePerl, platform-agnostic)
- Build uses `perl Makefile.PL` + `make` + `make install`
- R32: settings.os check uses `in ("Linux", "OHOS")`
- R26: Not applicable (PurePerl module, no system-name library)
- R33: No shell env vars in build(), compiler flags from Perl itself
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ExtUtilsBuilderCompilerConan(ConanFile):
    name = "extutils-builder-compiler"
    version = "0.032"
    description = "An interface around different compilers"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/ExtUtils::Builder::Compiler"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Perl module dependencies are handled by the Perl runtime,
        # not by Conan. Dependencies (ExtUtils::Builder, ExtUtils::Config,
        # ExtUtils::Helpers) are PurePerl modules available in the Perl env.
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No autotools/cmake toolchain needed — Perl Makefile.PL handles everything
        pass

    def build(self):
        # Apply patches (none for this PurePerl module, but required by G1)
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Use absolute INSTALL_BASE pointing to staging dir in build folder
        install_base = os.path.join(self.build_folder, "lib", "perl5")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"')

        # Step 2: Build
        self.run("make -j1")

        # Step 3: Install to staging dir (no DESTDIR needed — INSTALL_BASE is absolute)
        self.run("make install")

    def package(self):
        # Copy installed Perl module files from build staging to package folder
        copy(self, "*.pm", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        # Copy pod files if any
        copy(self, "*.pod", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"), keep_path=True)

    def package_info(self):
        # This is a PurePerl module, not a C library
        # Set up the Perl library path for consumers
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")
        # MakeMaker installs modules under lib/perl5/$arch/ (e.g. aarch64-linux)
        # Find the arch-specific directory dynamically
        arch_dirs = glob.glob(os.path.join(perl_lib, "*"))
        for d in arch_dirs:
            if os.path.isdir(d):
                self.runenv_info.append_path("PERL5LIB", d)
                self.output.info(f"PERL5LIB arch path: {d}")
                break
        # Also add the top-level perl5 lib dir
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        # No cpp_info.libs — this is not a linkable C library
