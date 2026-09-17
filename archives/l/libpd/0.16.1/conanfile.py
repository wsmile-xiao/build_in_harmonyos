#!/usr/bin/env python3
"""Conan recipe — libpd 0.16.1 (upstream Makefile).

libpd embeds Pure Data as a portable audio synthesis library: Pure Data
itself is vendored by libpd through the pinned `pure-data` git submodule.
The GitHub archive of the 0.16.1 tag ships that directory EMPTY, so
source() also fetches the pinned submodule archive declared in
conandata.yml and unpacks it where the upstream Makefile expects it
(pure-data/src and pure-data/extra).

The upstream build system is a hand-written Makefile with no configure
script; it builds libs/libpd.so (target `libpd`) or libs/libpd.a (target
`libs/libpd.a`) and installs under include/libpd and lib.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class LibpdConan(ConanFile):
    name = "libpd"
    version = "0.16.1"
    description = "Pure Data as an embeddable audio synthesis library (libpd)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/libpd/libpd"
    url = "https://github.com/libpd/libpd"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    # R32: only Linux/OHOS are supported build hosts for this recipe.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]
        get(self, url=data["url"], sha256=data["sha256"], strip_root=True)
        # GitHub archives omit submodule content; inject the pinned snapshot
        # locally so no git or network access is needed while building.
        for name, sub in data.get("submodules", {}).items():
            get(self, **sub, destination=name, strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler and flags come from the Conan profile/toolchain, never
        # from a bare ${CC}/${CFLAGS} in the shell environment.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c") or "clang"
        tc = GnuToolchain(self)
        # GnuToolchain.defines yields bare macro names (no "-D" prefix), the
        # Autotools helpers add the prefix themselves — do the same here.
        cflags = " ".join(tc.cflags + [f"-D{define}" for define in tc.defines])
        # The upstream Makefile assigns CFLAGS with "=" (an inherited shell
        # CFLAGS is ignored) but exposes ADDITIONAL_CFLAGS/ADDITIONAL_LDFLAGS
        # hooks for exactly this purpose.  Its own platform detection branches
        # on `uname`, and on OHOS `uname -s` is "HarmonyOS", so the Linux arm
        # (-DHAVE_ALLOCA_H / -DHAVE_LIBDL / -ldl) never triggers: the three
        # feature macros are probed as present in the OHOS sysroot, so inject
        # them explicitly.  -ldl keeps the Linux path working too (libdl is a
        # no-op shim on OHOS, the symbols live in libc).
        feature_cflags = "-DHAVE_ALLOCA_H -DHAVE_LIBDL"
        # The upstream link line sets no DT_SONAME, which the local CI SONAME
        # quality gate (L5a) rejects and which makes downstream CMakeDeps
        # fall back to IMPORTED_NO_SONAME.  The installed artifact is the
        # unversioned libpd.so, so name it accordingly.
        extra_ldflags = '-ldl -Wl,-soname,libpd.so'
        target = "libpd" if self.options.shared else "libs/libpd.a"
        # R9: keep the build single job.
        self.run(
            f'make {target} -j1 CC="{cc}" '
            f'ADDITIONAL_CFLAGS="{cflags} {feature_cflags}" '
            f'ADDITIONAL_LDFLAGS="{extra_ldflags}"',
            cwd=self.source_folder,
        )

    def package(self):
        # `make install` has no DESTDIR indirection, so point prefix directly
        # at the package folder.  It installs the public headers under
        # include/libpd (plus util/ and the C++ wrappers) and the library.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c") or "clang"
        self.run(
            f'make install prefix="{self.package_folder}" CC="{cc}"',
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.libs = ["pd"]
        # Headers are installed under include/libpd, so expose that directory
        # (and its util/ subdirectory) directly for `#include "z_libpd.h"`.
        self.cpp_info.includedirs = ["include/libpd", "include/libpd/util", "include"]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
