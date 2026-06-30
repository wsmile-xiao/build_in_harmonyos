#!/usr/bin/env python3
"""Conan recipe for perl-scope-upper 0.34 (Scope::Upper).

XS module — operates on upper call stack frames.
Build system: ExtUtils::MakeMaker (Makefile.PL) + xsubpp + clang.

Note: On OHOS/HMDFS, .so dlopen is restricted by SELinux (hmdfs context).
The .so is signed with binary-sign-tool for HarmonyOS compatibility.
Runtime loading requires installation to system perl path (hnp_file context).
Compile stage is unaffected — .so generation success = built status.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlScopeUpperConan(ConanFile):
    name = "perl-scope-upper"
    version = "0.34"
    description = "Scope::Upper - Act on upper scopes (XS module)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Scope-Upper"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: OHOS platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

    def build(self):
        apply_conandata_patches(self)
        # XS module build: perl Makefile.PL → xsubpp → clang → .so
        # INSTALLDIRS=site installs to site_perl directory
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to package folder via DESTDIR
        self.run(f'make install DESTDIR="{self.package_folder}"',
                 cwd=self.source_folder)

        # Create lib/ with .so copy for G4 artifact check
        lib_out = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_out, exist_ok=True)

        so_files = glob.glob(
            os.path.join(self.package_folder, "**", "*.so"), recursive=True
        )
        # Sign ELF .so files for HarmonyOS (P-SIGN-001)
        # SELinux/hnp_file context required for dlopen; self-sign enables loading
        for so_file in so_files:
            # Remove old .codesign section if present (non-fatal if absent)
            try:
                self.run(f'llvm-objcopy --remove-section .codesign "{so_file}"',
                         cwd=self.source_folder)
            except Exception:
                pass
            # Self-sign the .so for HarmonyOS
            self.run(f'binary-sign-tool sign -inFile "{so_file}" '
                     f'-outFile "{so_file}" -selfSign 1',
                     cwd=self.source_folder)
            # Copy signed .so to lib/ for standard artifact discovery
            shutil.copy2(so_file, os.path.join(lib_out, os.path.basename(so_file)))

    def package_info(self):
        # XS module: .so is loaded by Perl's XSLoader/DynaLoader
        self.cpp_info.libs = []
        perl_arch = "aarch64-linux" if str(self.settings.arch) in ("armv8", "aarch64") else "x86_64-linux"
        perl_ver = "5.42.0"
        lib_base = os.path.join(
            "data", "service", "hnp", "perl.org", f"perl_{perl_ver}",
            "lib", "site_perl", perl_ver, perl_arch
        )
        # Set libdirs to the .so directory for G4 artifact check
        self.cpp_info.libdirs = [os.path.join(lib_base, "auto", "Scope", "Upper")]
        # Set PERL5LIB for runtime usage — must use absolute path via package_folder
        perllib = os.path.join(self.package_folder, lib_base)
        self.runenv_info.define("PERL5LIB", perllib)
