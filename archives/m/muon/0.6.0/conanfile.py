#!/usr/bin/env python3
"""Conan recipe for muon 0.6.0 — Meson-compatible build system written in C.

muon is a self-hosting meson-compatible build system. It produces a single
executable `muon`.

Build system: bootstrap (bootstrap.sh compiles src/amalgam.c with c99/clang,
then the bootstrapped muon configures and compiles the full build via an
internal samurai backend). libarchive/libcurl disabled (optional deps not
published); samurai enabled (embedded backend avoids external ninja).

Platform notes (HarmonyOS / OHOS):
  - No configure script; bootstrap uses ${CC:-c99} from the environment, so
    CC/CFLAGS/LDFLAGS come from the Conan toolchain (R33).
  - libcurl/libarchive/libpkgconf are optional and disabled to keep the
    dependency set minimal (none of them are required by the core tool).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class MuonConan(ConanFile):
    name = "muon"
    version = "0.6.0"
    description = "Meson-compatible build system written in C (abuild-muon upstream)"
    license = "GPL-3.0-only AND Apache-2.0"
    homepage = "https://muon.build/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in source directory — bootstrap + samurai backend are
        # in-source; out-of-source builds are not supported by bootstrap.
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain generates CC, CFLAGS, LDFLAGS env vars from the
        # Conan profile. R33: All flags come from Conan toolchain, no shell
        # env vars in build().
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Bootstrap: build a minimal muon from the amalgamated source
        self.run("./bootstrap.sh ./build-boot", env="conanbuild")
        # Use the bootstrapped muon to configure the final build
        # (libarchive/libcurl/libpkgconf disabled; samurai embedded;
        # meson-docs disabled — its genrefman.py needs PyYAML CLoader,
        # which is unavailable in the CI worker environment)
        self.run(
            "./build-boot/muon-bootstrap setup "
            "-Dlibarchive=disabled -Dlibcurl=disabled -Dlibpkgconf=disabled "
            "-Dsamurai=enabled -Dmeson-docs=disabled -Dprefix=/ build-final",
            env="conanbuild",
        )
        # Compile: the bootstrapped muon cannot run the default build action,
        # so drive the generated build.ninja with ninja (from buildenv PATH,
        # e.g. /data/service/hnp/bin/ninja; R9: -j1).
        self.run("ninja -C build-final -j1", env="conanbuild")

    def package(self):
        # muon is a CLI tool — copy binary and man pages
        copy(self, "muon", src=os.path.join(self.build_folder, "build-final"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "muon.1", src=os.path.join(self.build_folder, "build-final", "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "meson-reference.3", src=os.path.join(self.build_folder, "build-final", "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man3"))

    def package_info(self):
        # Application: expose bin/ for consumers
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
