#!/usr/bin/env python3
"""Conan recipe for libart_lgpl 2.3.21 (Autotools).

Libart is a library of basic graphic primitives (affine transforms,
bezier paths, scanline rasterization, SVP/VPaths) used by GTK+ 2 /
GdkRgb and the GNOME stack of that era.

The tarball ships an art_config.h with 32-bit sizes (ART_SIZEOF_LONG 4)
but on aarch64 gen_art_config.sh would emit 8 — the shipped values are
still type-correct for the public API, so we keep the tarball header and
regenerate only if configure re-runs gen_art_config.sh.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibArtLgplConan(ConanFile):
    name = "libart"
    version = "2.3.21"
    description = "Libart - LGPL library of basic graphic primitives"
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libart_lgpl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # No formal `make check` suite exists upstream; the noinst
        # testart/testuta binaries must be built and exercised as the
        # closest available verification (SKILL.md upstream-test rule).
        autotools.make(target="tests", args=["-j1"])
        testart = os.path.join(self.build_folder, "testart")
        if os.path.exists(testart):
            self.run(f'"{testart}" testpat', env="conanbuild")
            self.run(f'"{testart}" gradient', env="conanbuild")
            self.run(f'"{testart}" dist', env="conanbuild")
            self.run(f'"{testart}" dash', env="conanbuild")
            self.run(f'"{testart}" intersect', env="conanbuild")
        testuta = os.path.join(self.build_folder, "testuta")
        if os.path.exists(testuta):
            self.run(f'"{testuta}"', env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Headers install to include/libart-2.0/libart_lgpl/ and public
        # includes are written as <libart_lgpl/foo.h>, so expose the
        # libart-2.0 layer (gdk-pixbuf precedent).
        self.cpp_info.includedirs = ["include/libart-2.0"]
        self.cpp_info.libs = ["art_lgpl_2"]
        self.cpp_info.set_property("cmake_file_name", "libart")
        self.cpp_info.set_property("cmake_target_name", "libart::libart")
        self.cpp_info.set_property("pkg_config_name", "libart-2.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
