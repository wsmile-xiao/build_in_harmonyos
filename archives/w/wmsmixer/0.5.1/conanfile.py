#!/usr/bin/env python3
"""Conan recipe — wmsmixer 0.5.1 (Window Maker mixer dockapp, Imakefile→direct clang++ build).

Upstream uses the Imakefile/xmkmf (imake) build system; neither the local
environment nor CI ships the imake toolchain, so build() compiles the single
source file wmsmixer.cc (plus mixctl.h header) directly with clang++ and links
the X11/XPM/XShape extension libraries. Manual build verified (arm64 ELF).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class WmsmixerConan(ConanFile):
    name = "wmsmixer"
    version = "0.5.1"
    description = "wmsmixer 0.5.1 — Window Maker mixer dockapp with scroll-wheel volume control"
    license = "GPL-2.0"
    homepage = "https://www.hibernaculum.net/wmsmixer.html"
    url = "https://www.hibernaculum.net/wmsmixer.html"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 deps (all published on ohpcd); X11/X.h protocol headers come from xorgproto transitively
        self.requires("libx11/6.4.0")
        self.requires("libxpm/3.5.17")
        self.requires("libxext/6.4.0.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Upstream Imakefile relies on xmkmf/imake (CC = c++ -m32, 32-bit flag unusable on
        # arm64) and is not available on this toolchain; compile wmsmixer.cc directly.
        incs = ""
        libdirs = ""
        for dep in self.dependencies.values():
            for inc in dep.cpp_info.includedirs:
                incs += f" -I{os.path.join(dep.package_folder, inc)}"
            for lib in dep.cpp_info.libdirs:
                libdirs += f" -L{os.path.join(dep.package_folder, lib)}"
        # C++ compiler comes from the Conan toolchain conf (R33: no bare shell env vars).
        cxx = self._get_cxx()
        self.run(
            f"{cxx} -O2 -fPIC -std=c++17 {incs} wmsmixer.cc -o wmsmixer {libdirs} -lX11 -lXpm -lXext",
            env="conanbuild", cwd=self.source_folder)

    def _get_cxx(self):
        # Resolve the C++ compiler executable from the Conan toolchain config
        # (tools.build:compiler_executables set by the OHOS profile), falling back
        # to the compiler family name from settings. Never uses bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp")
        if cxx:
            return cxx
        f = self.settings.get_safe("compiler")
        if f == "clang":
            cxx = "clang++"
        elif f == "gcc":
            cxx = "g++"
        else:
            raise ConanException(f"Unsupported compiler family: {f!r}; set tools.build:compiler_executables in profile")
        return cxx

    def package(self):
        copy(self, "wmsmixer", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "wmsmixer"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.conf_info.define("user.wmsmixer:bin", "wmsmixer")