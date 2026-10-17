#!/usr/bin/env python3
"""Conan recipe — Perl XS module (ExtUtils::MakeMaker / Makefile.PL).

Proc::Wait3 - Perl extension for wait3 system call (XS/C module).
Build system: perl Makefile PL (ExtUtils::MakeMaker).

Adaptations for OHOS:
- Uses INSTALL_BASE to install to a known path (avoids hardcoding Perl version)
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlProcWait3Conan(ConanFile):
    name = "perl-proc-wait3"
    version = "0.05"
    description = "Perl extension for wait3 system call (XS/C module)"
    license = "perl_5"
    homepage = "https://metacpan.org/pod/Proc::Wait3"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No autotools/cmake toolchain needed — Perl Makefile.PL handles everything
        pass

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Use INSTALL_BASE to install to a known location in build folder
        # This avoids hardcoding Perl version paths (perl_5.42.x) in package()
        install_base = os.path.join(self.build_folder, "lib", "perl5")

        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"')
        self.run("make -j1")
        self.run("make install")

    def package(self):
        # Copy installed files from build staging to package folder
        copy(self, "*.so", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pm", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # This is a Perl XS module, not a C library
        # The .so is loaded by Perl's XSLoader at runtime
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
        # No cpp_info.libs — this is not a linkable C library
