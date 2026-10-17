#!/usr/bin/env python3
"""Conan recipe — libequihash 1.0.10 (Makefile).

Equihash memory-hard proof-of-work library with fast verification.
Upstream builds libequihash.so / libequihash.a / equihash CLI from a plain
Makefile and links libsodium (-lsodium) for a single call:
crypto_generichash(out, outlen, in, inlen, NULL, 0), i.e. keyless BLAKE2b.
This recipe vendors a minimal RFC 7693 BLAKE2b (vendor/blake2b.{h,c}, CC0)
that is bit-identical for that call, so there are zero external requires and
no Autotools configure step (libsodium's configure re-execs
CONFIG_SHELL=/data/service/hnp/bin/bash, which is inaccessible on the OHOS
preflight host). This recipe packages the library (static or shared) plus
the public header; the CLI binary is not packaged (its link line needs
-lstdc++, which the OHOS clang/libc++ toolchain does not provide), so the
package stays a pure library (R38: no commands.json).
Upstream ships no test suite (no check/test target, no tests/ directory),
so build() runs no upstream tests; the no_tests audit lives in
test_package/MANIFEST.yml.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibequihashConan(ConanFile):
    name = "libequihash"
    version = "1.0.10"
    description = "Equihash memory-hard proof-of-work library with fast verification (C API: solsize/solve/verify)"
    license = "CC0-1.0"
    homepage = "https://github.com/stef/equihash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*", src=os.path.join(self.recipe_folder, "vendor"),
             dst=os.path.join(self.export_sources_folder, "vendor"))

    # No external requires: the only hash used (keyless BLAKE2b) is vendored
    # (vendor/blake2b.{h,c}), so no Autotools dependency is ever built.

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libequihash supports Linux and OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        copy(self, "*", src=os.path.join(self.export_sources_folder, "vendor"),
             dst=self.source_folder)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler tools come from Conan conf, never from shell env.
        # Preflight /bin/sh (toybox) reports absolute HNP paths as
        # "inaccessible or not found" even when present; hmbs guarantees the
        # toolchain via buildenv PATH, so resolve to PATH lookup (basename).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}

        def _tool(key, fallback):
            v = compilers.get(key) or fallback
            if "/" in v:
                v = os.path.basename(v) or v
            return v

        cc = _tool("c", "clang")
        cxx = _tool("cpp", "clang++")
        ar = _tool("ar", "ar")
        # Compile the vendored keyless BLAKE2b (replaces -lsodium).
        # env="conanbuild" exposes hmbs PATH/TMPDIR (avoids readonly /tmp).
        self.run(
            "\"%s\" -O2 -std=c99 -c \"%s\" -o \"%s\""
            % (
                cc,
                os.path.join(self.source_folder, "blake2b.c"),
                os.path.join(self.source_folder, "blake2b.o"),
            ),
            env="conanbuild",
        )
        # SYS is passed explicitly so make never spawns `gcc -dumpmachine`
        # (absent on OHOS); that probe only gates an x86-only flag anyway.
        # LIBS="" drops the upstream -lsodium link; the vendored blake2b.o
        # rides via EXTRA_SOURCES (both the .so link and the compile lines
        # consume $(CXXFLAGS) $(EXTRA_CXXFLAGS)). Only the library targets
        # are built: the `equihash` CLI link line needs -lstdc++, which the
        # OHOS clang/libc++ toolchain does not provide; bench/CLI are not
        # packaged. R9: -j1 (OHOS jobserver restriction).
        self.run(
            "make -C \"%s\" -j1 CC=\"%s\" CXX=\"%s\" AR=\"%s\" "
            "SYS=\"aarch64-linux-ohos\" LIBS=\"\" "
            "EXTRA_SOURCES=\"blake2b.o\" "
            "EXTRA_CXXFLAGS=\"-fstack-clash-protection\" "
            "libequihash.so libequihash.a"
            % (
                self.source_folder,
                cc,
                cxx,
                ar,
            ),
            env="conanbuild",
        )
        # The upstream `libequihash.a` rule archives only equihash.o, so
        # append the vendored object to the static library as well.
        self.run(
            "\"%s\" rcs \"%s\" \"%s\""
            % (
                ar,
                os.path.join(self.source_folder, "libequihash.a"),
                os.path.join(self.source_folder, "blake2b.o"),
            ),
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "equihash.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "libequihash.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        if self.options.shared:
            copy(
                self,
                "libequihash.so",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "lib"),
            )
            # Upstream DT_SONAME is libequihash.so.0; provide that link.
            so_link = os.path.join(self.package_folder, "lib", "libequihash.so.0")
            try:
                if os.path.islink(so_link) or os.path.exists(so_link):
                    os.remove(so_link)
                os.symlink("libequihash.so", so_link)
            except OSError:
                shutil.copy2(
                    os.path.join(self.package_folder, "lib", "libequihash.so"),
                    so_link,
                )

    def package_info(self):
        self.cpp_info.libs = ["equihash"]
        if self.settings.os == "OHOS":
            # Static consumers link the C++ objects with the C driver;
            # libc++ provides the runtime on OHOS (profile: compiler.libcxx=libc++).
            self.cpp_info.system_libs = ["c++"]
