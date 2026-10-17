#!/usr/bin/env python3
"""Conan recipe — Crypt::Eksblowfish (Perl XS module with ExtUtils::MakeMaker).

Crypt::Eksblowfish implements the Eksblowfish block cipher (used by bcrypt).
This is a Perl XS module built with ExtUtils::MakeMaker (Makefile.PL), containing
compiled C code (Eksblowfish.xs → Eksblowfish.so).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
The .so is loaded by Perl's XSLoader/DynaLoader at runtime.

Adaptations for OHOS:
- CPATH/LIBRARY_PATH set to OHOS SDK sysroot for musl headers
- PERL5LIB set to user-installed Perl module path
- Makefile.PL patched to replace Module::Build passthrough with standalone
  ExtUtils::MakeMaker version; cleans -fstack-protector-strong from ldflags (E137)
- R32: settings.os check uses `in ("Linux", "OHOS")`
- R33: build environment via Conan buildenv_info, not raw os.environ
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlCryptEksblowfishConan(ConanFile):
    name = "perl-crypt-eksblowfish"
    version = "0.009-r15"
    description = "Eksblowfish block cipher (Perl XS module, used by bcrypt)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Crypt-Eksblowfish"
    url = ""  # CI fills this

    # XS module compiles C code — needs compiler/build_type
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # R27: dependencies must use @ohpcd/stable
        # Perl is a system dependency, not a Conan package
        # Required Perl modules: Class::Mix, MIME::Base64, XSLoader, parent
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_sysroot(self):
        """Resolve OHOS SDK sysroot path."""
        sysroot = os.environ.get("OHOS_SYSROOT")
        if sysroot and os.path.isdir(sysroot):
            return sysroot
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot",
            os.path.expanduser("~/ohos-sdk/sysroot"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        raise ConanException(
            "Cannot find OHOS SDK sysroot. Set OHOS_SYSROOT environment variable."
        )

    def _resolve_perl_lib(self):
        """Resolve Perl module library path for PERL5LIB."""
        perl_lib = os.environ.get("PERL5LIB")
        if perl_lib:
            return perl_lib
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, "usr/local/lib/perl5/aarch64-linux"),
            os.path.join(home, "usr/local/lib/perl5"),
            "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux",
            "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0",
            "/data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux",
            "/data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0",
        ]
        existing = [c for c in candidates if os.path.isdir(c)]
        return ":".join(existing) if existing else ""

    def generate(self):
        sysroot = self._resolve_sysroot()
        perl_lib = self._resolve_perl_lib()

        # R33: use buildenv_info exclusively, no raw os.environ writes
        # CPATH: OHOS SDK sysroot headers
        cpath = os.path.join(sysroot, "usr", "include")
        self.buildenv_info.define("CPATH", cpath)

        # LIBRARY_PATH: sysroot libs
        lib_path = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
        self.buildenv_info.define("LIBRARY_PATH", lib_path)

        # LD_LIBRARY_PATH: OHOS SDK llvm/lib — lld linker depends on libxml2.so.16
        sdk_native = os.path.dirname(os.path.normpath(sysroot))
        llvm_lib = os.path.join(sdk_native, "llvm", "lib")
        if os.path.isdir(llvm_lib):
            self.buildenv_info.define("LD_LIBRARY_PATH", llvm_lib)

        # PERL5LIB: Perl module path
        if perl_lib:
            self.buildenv_info.define("PERL5LIB", perl_lib)

    def build(self):
        # Apply patches (Makefile.PL: replace Module::Build passthrough with ExtUtils::MakeMaker)
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker (Makefile.PL patch handles ldflags cleanup)
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Build (Makefile.PL patch cleans -fstack-protector-strong from Config)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts from blib to package folder in standard layout
        # .so goes to lib/perl5/aarch64-linux/auto/Crypt/Eksblowfish/ (Perl auto path)
        # .pm goes to lib/perl5/aarch64-linux/Crypt/Eksblowfish/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        # Eksblowfish.so (XS extension)
        copy(self, "Eksblowfish.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "Eksblowfish"),
             dst=os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "auto", "Crypt", "Eksblowfish"))
        copy(self, "Eksblowfish.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "Eksblowfish"),
             dst=os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "auto", "Crypt", "Eksblowfish"))

        # Eksblowfish.pm (main module)
        copy(self, "Eksblowfish.pm",
             src=os.path.join(blib_lib, "Crypt"),
             dst=os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "Crypt"))

        # Subpackage .pm files
        copy(self, "*.pm",
             src=os.path.join(blib_lib, "Crypt", "Eksblowfish"),
             dst=os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "Crypt", "Eksblowfish"))

    def package_info(self):
        # Perl XS module: .so is loaded by Perl DynaLoader, not linked by CMake
        # R26: non-system library, default dynamic linking
        self.cpp_info.libs = []  # No C/C++ libraries to link (Perl DynaLoader loads .so)
        self.cpp_info.libdirs = ["lib/perl5/aarch64-linux/auto/Crypt/Eksblowfish"]
        self.cpp_info.includedirs = []

        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        perl_arch_lib = os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.runenv_info.append_path("PERL5LIB", perl_arch_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_arch_lib)
