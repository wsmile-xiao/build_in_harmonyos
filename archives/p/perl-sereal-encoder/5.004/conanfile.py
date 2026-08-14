#!/usr/bin/env python3
"""Conan recipe for perl-sereal-encoder 5.004 (Sereal::Encoder).

XS module — Sereal binary serialization format encoder.
Build system: ExtUtils::MakeMaker (Makefile.PL) + xsubpp + clang.
Bundled libraries: miniz, csnappy, zstd (compiled statically into .so).

OHOS adaptations:
- ELF signing: llvm-objcopy + binary-sign-tool (required for .so dlopen)
- .so runtime loading in conan cache blocked by file permission model (E046)
- test_package: static checks + runtime Sereal::Encoder API call (R34, E046 tolerated)
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlSerealEncoderConan(ConanFile):
    name = "perl-sereal-encoder"
    version = "5.004"
    description = "Sereal::Encoder - XS-based Sereal binary serialization encoder for Perl"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Sereal-Encoder"
    url = "https://metacpan.org/dist/Sereal-Encoder"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: settings.os judgment must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. Only Linux and OHOS are supported."
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # XS module: no autotools configure, just perl Makefile.PL
        pass

    def build(self):
        apply_conandata_patches(self)

        # XS module build: perl Makefile.PL → xsubpp → clang → .so
        # Env vars to skip interactive prompts and use bundled libs:
        #   USE_UNALIGNED=1 - enable unaligned loads for performance
        #   NO_ASM=1 - disable assembly in bundled zstd (cross-compile safe)
        #   CPAN_COMPAT=1 - skip prompts in CPAN mode
        #   SEREAL_USE_BUNDLED_LIBS=1 - skip Devel::CheckLib probes (avoids hang on OHOS)
        os.environ["USE_UNALIGNED"] = "1"
        os.environ["NO_ASM"] = "1"
        os.environ["CPAN_COMPAT"] = "1"
        os.environ["SEREAL_USE_BUNDLED_LIBS"] = "1"

        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j2", cwd=self.source_folder)

    def package(self):
        # Install to package folder directly via DESTDIR
        self.run(f'make install DESTDIR="{self.package_folder}"',
                 cwd=self.source_folder)

        # Create lib/ with signed .so copy for G4 artifact check + consumers
        lib_out = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_out, exist_ok=True)

        so_files = glob.glob(
            os.path.join(self.package_folder, "**", "*.so"), recursive=True
        )

        # Sign ELF .so files for HarmonyOS (P-SIGN-001)
        # musl dynamic linker checks .codesign section; unsigned .so = Permission denied
        for so_file in so_files:
            # Remove old .codesign section if present (fresh builds have no signature yet)
            # ConanException expected when section doesn't exist — not a real error
            try:
                self.run(f'llvm-objcopy --remove-section .codesign "{so_file}"',
                         cwd=self.source_folder)
            except ConanException:
                pass  # .codesign section absent on fresh builds
            # Self-sign the .so for HarmonyOS
            self.run(f'binary-sign-tool sign -inFile "{so_file}" '
                     f'-outFile "{so_file}" -selfSign 1',
                     cwd=self.source_folder)
            # Copy signed .so to lib/ for standard artifact discovery
            shutil.copy2(so_file, os.path.join(lib_out, os.path.basename(so_file)))

    def package_info(self):
        # XS module: .so is loaded by Perl's XSLoader/DynaLoader
        self.cpp_info.libs = ["Encoder"]
        perl_arch = "aarch64-linux" if str(self.settings.arch) in ("armv8", "aarch64") else "x86_64-linux"
        perl_ver = "5.42.0"
        lib_base = os.path.join(
            "data", "service", "hnp", "perl.org", f"perl_{perl_ver}",
            "lib", "site_perl", perl_ver, perl_arch
        )
        # Set libdirs to the .so directory for G4 artifact check
        self.cpp_info.libdirs = [os.path.join(lib_base, "auto", "Sereal", "Encoder")]
        # Set PERL5LIB for runtime usage — must use absolute path via package_folder
        perllib = os.path.join(self.package_folder, lib_base)
        self.runenv_info.define("PERL5LIB", perllib)
