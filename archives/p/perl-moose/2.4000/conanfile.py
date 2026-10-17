#!/usr/bin/env python3
"""Conan recipe — Moose Perl XS module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C/XS sources into a shared library
(Moose.so) loaded by Perl's XSLoader/DynaLoader at runtime.

Adaptations for OHOS:
- Bypass can_compile_loadable_object check (HMDFS blocks dlopen, ld.lld rejects -fstack-protector-strong)
- Pure Perl fallback for Class::MOP when XS .so cannot be loaded (HMDFS SELinux)
- R32: settings.os check uses `in ("Linux", "OHOS")`
- R33: Build uses perl Makefile.PL which handles compiler selection internally
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlMooseConan(ConanFile):
    name = "perl-moose"
    version = "2.4000"
    description = "A postmodern object system for Perl 5"
    license = "perl_artistic"
    homepage = "https://metacpan.org/dist/Moose"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Perl XS module dependencies are handled at the Perl/system level,
        # not as Conan packages. See notes.md for dependency installation.
        pass

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

        # Use absolute INSTALL_BASE pointing to staging dir in build folder
        install_base = os.path.join(self.build_folder, "lib", "perl5")

        # Unset LD env var: ExtUtils::HasCompiler::Config::get() checks $ENV{LD}
        # first, which is set to ld.lld in the environment. ld.lld doesn't
        # understand -fstack-protector-strong from Perl's lddlflags.
        # The Makefile.PL patch bypasses can_compile_loadable_object anyway,
        # but unsetting LD ensures the actual build uses clang as linker.
        old_ld = os.environ.pop("LD", None)

        try:
            # Step 1: Generate Makefile using ExtUtils::MakeMaker
            self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"')

            # Step 2: Build
            self.run("make -j1")

            # Step 3: Install to staging dir (no DESTDIR needed — INSTALL_BASE is absolute)
            self.run("make install")
        finally:
            if old_ld is not None:
                os.environ["LD"] = old_ld

    def package(self):
        # Copy installed files from build staging to package folder
        copy(self, "*.so", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pm", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pod", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        # Copy the bin script (moose-outdated)
        copy(self, "*", src=os.path.join(self.build_folder, "lib", "perl5", "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # This is a Perl XS module, not a C library
        # The .so is loaded by Perl's XSLoader at runtime
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
        # Declare bin directory for moose-outdated script
        self.cpp_info.bindirs = [os.path.join(self.package_folder, "bin")]
        # No cpp_info.libs — this is not a linkable C library
