#!/usr/bin/env python3
"""Conan recipe for xsct 2.3 — X11 set color temperature tool.

xsct is a small C program that sets the screen color temperature via XRandR.
It produces a single CLI executable (not a library).
Build system: simple Makefile (no autotools).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class XsctConan(ConanFile):
    name = "xsct"
    version = "2.3"
    description = "Xsct (X11 set color temperature) - set screen color temperature via XRandR"
    license = "Unlicense"
    homepage = "https://github.com/faf0/sct"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        copy(self, "Makefile", src=self.recipe_folder, dst=self.export_sources_folder)

    def configure(self):
        self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxrandr/1.5.5.1", transitive_headers=True, transitive_libs=True)
        # Xatom.h is in xorgproto
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # Xrender.h is in libxrender (transitive via libxrandr→libxext→libxrender)
        self.requires("libxrender/0.9.12", transitive_headers=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xsct supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply any patches from conandata.yml (required by G1 check)
        apply_conandata_patches(self)

        # Get dependency paths
        libx11 = self.dependencies["libx11"].cpp_info
        libxrandr = self.dependencies["libxrandr"].cpp_info
        xorgproto = self.dependencies["xorgproto"].cpp_info
        libxrender = self.dependencies["libxrender"].cpp_info

        x11_inc = libx11.includedirs[0]
        xrandr_inc = libxrandr.includedirs[0]
        xorgproto_inc = xorgproto.includedirs[0]
        xrender_inc = libxrender.includedirs[0]
        x11_lib = libx11.libdirs[0]
        xrandr_lib = libxrandr.libdirs[0]

        # Override Makefile variables via command line (Makefile uses ?=)
        cflags = f"-Wall -Wextra -std=c99 -O2 -I{x11_inc} -I{xrandr_inc} -I{xorgproto_inc} -I{xrender_inc}"
        ldflags = f"-L{x11_lib} -L{xrandr_lib}"

        self.run(
            f"make -C {self.source_folder} -j1 "
            f"CC=clang CFLAGS='{cflags}' LDFLAGS='{ldflags}'"
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "xsct"),
            os.path.join(bindir, "xsct"),
        )
        # Copy man page
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(mandir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "xsct.1"),
            os.path.join(mandir, "xsct.1"),
        )
        # License
        licdir = os.path.join(self.package_folder, "licenses")
        os.makedirs(licdir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "LICENSE"),
            os.path.join(licdir, "LICENSE"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
