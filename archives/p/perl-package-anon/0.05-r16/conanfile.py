#!/usr/bin/env python3
"""Conan recipe — Package::Anon (Perl XS module)

A Perl XS module that provides anonymous packages.
Uses ExtUtils::MakeMaker (Makefile.PL) as build system.

Platform note: On OHOS, Perl's Config incpth points to non-existent paths.
We patch the Makefile's CCFLAGS/LDDLFLAGS with explicit OHOS SDK sysroot paths.
Additionally, OHOS lacks CRT files (crti.o, crtn.o, crtbeginS.o, crtendS.o),
so we add -nostartfiles -nodefaultlibs -lc to LDDLFLAGS as fallback
(experience from perl-dbd-pg 3.18.0 adaptation).
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# OHOS SDK paths — use env vars with fallback for portability
SYSROOT = os.environ.get(
    "OHOS_SYSROOT",
    "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot",
)
LLVM_LIB = os.environ.get(
    "OHOS_LLVM_LIB",
    "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
)
SYSROOT_INC = f"{SYSROOT}/usr/include"
SYSROOT_ARCH_INC = f"{SYSROOT}/usr/include/aarch64-linux-ohos"
SYSROOT_ARCH_LIB = f"{SYSROOT}/usr/lib/aarch64-linux-ohos"

# Extra CFLAGS to add OHOS SDK sysroot include paths
EXTRA_CCFLAGS = f"-isystem {SYSROOT_INC} -isystem {SYSROOT_ARCH_INC}"
# Extra LDDLFLAGS: sysroot + lib paths + CRT fallback (perl-dbd-pg experience)
EXTRA_LDDLFLAGS = f"--sysroot={SYSROOT} -L{SYSROOT_ARCH_LIB} -L{LLVM_LIB} -nostartfiles -nodefaultlibs -lc"


class PerlpackageanonConan(ConanFile):
    name = "perl-package-anon"
    version = "0.05-r16"
    description = "Package::Anon - Anonymous packages for Perl"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Package-Anon"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_makefile(self):
        """Patch generated Makefile to add OHOS SDK sysroot paths and CRT fallback."""
        makefile_path = os.path.join(self.source_folder, "Makefile")
        if not os.path.exists(makefile_path):
            return
        with open(makefile_path, "r") as f:
            content = f.read()
        # Add sysroot include paths to CCFLAGS
        content = re.sub(
            r"^(CCFLAGS = )",
            f"\\1{EXTRA_CCFLAGS} ",
            content,
            flags=re.MULTILINE,
        )
        # Add sysroot, lib paths and CRT fallback to LDDLFLAGS
        content = re.sub(
            r"^(LDDLFLAGS = )",
            f"\\1{EXTRA_LDDLFLAGS} ",
            content,
            flags=re.MULTILINE,
        )
        with open(makefile_path, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        # Perl XS module build: perl Makefile.PL && make
        self.run("perl Makefile.PL", cwd=self.source_folder)
        # Patch Makefile to add OHOS SDK sysroot paths for clang
        self._patch_makefile()
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install to package directory using DESTDIR
        self.run("make install DESTDIR={}".format(self.package_folder), cwd=self.source_folder)

    def package_info(self):
        # This is a Perl XS module, not a C library
        self.cpp_info.libs = []
