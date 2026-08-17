#!/usr/bin/env python3
"""Conan recipe for debianutils 5.23.2 — manual build (no autotools).

debianutils is a collection of Debian-specific utility programs including
run-parts, tempfile, ischroot, and several shell scripts. The source tarball
only contains configure.ac + Makefile.am (no pre-generated configure), so
we bypass autotools entirely and compile the 3 C files directly.

Platform adaptations for OHOS:
  1. No autoreconf needed — manual compilation avoids automake/aclocal dependency.
  2. Static linking for standalone executables.
  3. Shell scripts copied as-is (shebangs use /bin/sh which maps to /system/bin/sh).

R28: test_package/ exists.
R34: test_package invokes run-parts --version (real binary API call).
R38: commands.json declared at software level (tool-type package).
"""
import glob
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class DebianutilsConan(ConanFile):
    name = "debianutils"
    version = "5.23.2"
    description = "Miscellaneous utilities specific to Debian (run-parts, tempfile, ischroot)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/debianutils"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Use AutotoolsToolchain only for environment generation (CC, CFLAGS, LDFLAGS).
        # We don't run configure/make — compile C files manually in build().
        tc = AutotoolsToolchain(self)
        tc.extra_ldflags.append("-static")
        tc.generate()

        # lld linker depends on libxml2.so.16 in the LLVM lib directory.
        # CI workers may not have this in LD_LIBRARY_PATH by default.
        env = Environment()
        for lib_dir in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isfile(os.path.join(lib_dir, "libxml2.so.16")):
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                break
        env.vars(self).save_script("lld_fix")

    def build(self):
        apply_conandata_patches(self)
        # Compile 3 C files directly — no autoreconf/configure/make needed.
        # Defines normally provided by autotools config.h:
        #   PACKAGE_VERSION — from acinclude.m4 (upstream version, not Debian pkg version)
        #   HAVE_GETOPT_H / HAVE_PATHS_H — from AC_CHECK_HEADERS (verified in OHOS SDK)
        #   _FILE_OFFSET_BITS — from AC_SYS_LARGEFILE
        src = self.source_folder
        defines = "-DPACKAGE_VERSION='\"5.23.1\"' -DHAVE_GETOPT_H -DHAVE_PATHS_H -D_FILE_OFFSET_BITS=64"
        self.run(f"$CC $CFLAGS {defines} -o run-parts {src}/run-parts.c $LDFLAGS", env=["conanbuild", "lld_fix"])
        self.run(f"$CC $CFLAGS {defines} -o tempfile {src}/tempfile.c $LDFLAGS", env=["conanbuild", "lld_fix"])
        self.run(f"$CC $CFLAGS {defines} -o ischroot {src}/ischroot.c $LDFLAGS", env=["conanbuild", "lld_fix"])

    def package(self):
        # Install compiled binaries to bin/
        copy(self, "run-parts", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tempfile", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "ischroot", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Install shell scripts to bin/
        copy(self, "which.debianutils", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "savelog", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Install sbin scripts
        copy(self, "installkernel", src=self.source_folder, dst=os.path.join(self.package_folder, "sbin"))
        copy(self, "add-shell", src=self.source_folder, dst=os.path.join(self.package_folder, "sbin"))
        copy(self, "remove-shell", src=self.source_folder, dst=os.path.join(self.package_folder, "sbin"))
        copy(self, "update-shells", src=self.source_folder, dst=os.path.join(self.package_folder, "sbin"))
        # Install man pages
        copy(self, "*.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
