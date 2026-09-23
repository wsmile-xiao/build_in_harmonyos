#!/usr/bin/env python3
"""Conan recipe — nbimg 1.2.1 (smartphone boot splash screen converter).

nbimg converts boot splash screen images between BMP and NB/IMG formats for
Android and WinCE smartphones (HTC/Diamond era).  The upstream tarball is a
plain GNU-Make project (no configure); it builds a single C file `nbimg.c`
and produces one CLI binary `nbimg`.

OHOS notes:
  * The upstream `all` target also builds a `win32` cross variant via
    `i586-mingw32msvc-gcc`, which is unavailable in the OHOS build sandbox;
    we build only the native `nbimg` target (no platform macro, pure
    Makefile target selection).
  * `install` from GNU coreutils is not used; package() copies the produced
    binary and the upstream README/LICENSE directly.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class NbimgConan(ConanFile):
    name = "nbimg"
    version = "1.2.1"
    description = "Smartphone boot splash screen converter (Android and WinCE), NB <-> BMP"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/poliva/nbimg"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("splash", "bmp", "nb", "converter", "htc", "wince")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Upstream uses a plain in-source Makefile (no VPATH) -> force
        # in-source build so `make` sees its own sources.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler must come from the Conan toolchain, never from an
        # undefined shell var (empty on release workers).
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp.get("c") or os.environ.get("CC") or "clang"
        # Build only the native `nbimg` target: the upstream `all` target
        # triggers the `win32` cross build (i586-mingw32msvc-gcc) which is
        # not available in the OHOS sandbox.
        self.run(f"make -j1 nbimg CC={cc} CFLAGS=\"-fPIC -O2\"")

    def package(self):
        copy(self, "nbimg", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README.md", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "nbimg"))
        copy(self, "LICENSE", src=self.build_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Pure command-line tool: no libraries or headers to expose.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))