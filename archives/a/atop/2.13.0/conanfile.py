#!/usr/bin/env python3
"""Conan recipe for atop 2.13.0 — System and process monitor for Linux.

Builds atop CLI tools (atop, atopsar, atopacctd, atopconvert, atopcat, atophide)
from the upstream Makefile with HarmonyOS patches.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# qsort_r compatibility shim — HarmonyOS libc does not export qsort_r
QSORT_R_COMPAT = """/*
 * qsort_r compatibility shim for HarmonyOS
 *
 * HarmonyOS (musl-based) libc does not export qsort_r.
 * This provides a simple non-thread-safe wrapper around qsort
 * using static storage for the comparator argument.
 * atop is single-threaded so this is safe.
 */

#include <stdlib.h>

static void   *qsort_r_arg;
static int   (*qsort_r_cmp)(const void *, const void *, void *);

static int
qsort_r_wrapper(const void *a, const void *b)
{
    return qsort_r_cmp(a, b, qsort_r_arg);
}

void
qsort_r(void *base, size_t nmemb, size_t size,
        int (*compar)(const void *, const void *, void *),
        void *arg)
{
    qsort_r_arg = arg;
    qsort_r_cmp = compar;
    qsort(base, nmemb, size, qsort_r_wrapper);
}
"""


class AtopConan(ConanFile):
    name = "atop"
    version = "2.13.0"
    description = "System and process monitor for Linux"
    license = "GPL-2.0"
    homepage = "https://www.atoptool.nl/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = "VirtualBuildEnv", "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.0.1")
        self.requires("ncurses/6.6")
        # zlib comes transitively from glib as 1.3.1.1.1.1
        self.requires("zlib/1.3.1.1.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS"
            )

    def build(self):
        apply_conandata_patches(self)

        # Write qsort_r compatibility shim (new file not covered by patch)
        qsort_path = os.path.join(self.source_folder, "qsort_r_compat.c")
        with open(qsort_path, "w") as f:
            f.write(QSORT_R_COMPAT)

        # R33: Get compiler from Conan settings/conf, not shell env vars
        cc_executables = self.conf.get("tools.build:compiler_executables", default={})
        if cc_executables:
            if isinstance(cc_executables, str):
                import json
                cc_executables = json.loads(cc_executables)
            cc = cc_executables.get("c", str(self.settings.compiler))
        else:
            cc = str(self.settings.compiler)

        # Set PKG_CONFIG_PATH so pkg-config finds .pc files from PkgConfigDeps
        os.environ["PKG_CONFIG_PATH"] = self.generators_folder

        # PkgConfigDeps generates .pc files for all dependencies
        # Makefile uses pkg-config for glib-2.0; we pass ncursesw and zlib via CFLAGS/LDFLAGS
        self.run(
            f'make CC={cc} '
            f'CFLAGS="$(pkg-config --cflags ncursesw zlib)" '
            f'LDFLAGS="$(pkg-config --libs ncursesw zlib)" '
            f'-j1',
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        # Copy binaries to package folder
        bindir = os.path.join(self.package_folder, "bin")
        sbindir = os.path.join(self.package_folder, "sbin")
        copy(self, "atop", src=self.source_folder, dst=bindir)
        copy(self, "atopacctd", src=self.source_folder, dst=sbindir)
        copy(self, "atopconvert", src=self.source_folder, dst=bindir)
        copy(self, "atopcat", src=self.source_folder, dst=bindir)
        copy(self, "atophide", src=self.source_folder, dst=bindir)
        # Create atopsar symlink (atop binary invoked as atopsar)
        atopsar_path = os.path.join(bindir, "atopsar")
        if os.path.lexists(atopsar_path):
            os.remove(atopsar_path)
        os.symlink("atop", atopsar_path)
        # Man pages
        copy(self, "*.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*.5", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man5"))
        copy(self, "*.8", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
