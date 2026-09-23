#!/usr/bin/env python3
"""Conan recipe — open-tyrian 2.1.20221123

An open-source port of the scrolling shooter Tyrian.
Build system: plain Makefile (uses pkg-config for SDL2/SDL2_net).
License: GPL-2.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpentyrianConan(ConanFile):
    name = "open-tyrian"
    version = "2.1.20221123"
    description = "Open-source port of the scrolling shooter Tyrian"
    license = "GPL-2.0"
    homepage = "https://github.com/opentyrian/opentyrian"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("sdl2_net/2.2.0")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Create corrected .pc files for SDL2 and SDL2_net so the Makefile's
        # pkg-config calls resolve to Conan-managed dependency paths.
        # SDL2's Conan package provides a .pc file with prefix=/ (wrong);
        # SDL2_net has no .pc file (uses CMake targets).
        pc_dir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)

        sdl2 = self.dependencies["sdl2"]
        sdl2_net = self.dependencies["sdl2_net"]

        sdl2_root = sdl2.package_folder
        sdl2_net_root = sdl2_net.package_folder

        with open(os.path.join(pc_dir, "sdl2.pc"), "w") as f:
            f.write(
                f"prefix={sdl2_root}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: sdl2\n"
                f"Description: Simple DirectMedia Layer\n"
                f"Version: {sdl2.ref.version}\n"
                f"Libs: -L${{libdir}} -lSDL2 -lm -lpthread\n"
                f"Cflags: -I${{includedir}} -I${{includedir}}/SDL2 -D_REENTRANT\n"
            )

        with open(os.path.join(pc_dir, "SDL2_net.pc"), "w") as f:
            f.write(
                f"prefix={sdl2_net_root}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: SDL2_net\n"
                f"Description: SDL2 networking library\n"
                f"Version: {sdl2_net.ref.version}\n"
                f"Requires: sdl2\n"
                f"Libs: -L${{libdir}} -lSDL2_net\n"
                f"Cflags: -I${{includedir}} -I${{includedir}}/SDL2\n"
            )

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        pc_dir = os.path.join(self.build_folder, "pkgconfig")

        # Pre-create obj/ directory (HMDFS mkdir in make recipe may fail silently)
        obj_dir = os.path.join(self.source_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)

        # Pass key variables on the make command line to override both
        # Makefile defaults (?=) and environment variables:
        # - CC: from Conan conf (R33)
        # - CFLAGS: clang-compatible flags (avoid GCC-only -Wno-format-truncation)
        # - CPPFLAGS: reset to -MMD to avoid env-injected -I paths
        # - PKG_CONFIG_PATH: point to our corrected .pc files
        # - VCS_IDREV: explicit version string (Makefile defaults to git describe)
        # - INSTALL: OHOS has no 'install' command, use 'cp'
        self.run(
            f'export PKG_CONFIG_PATH="{pc_dir}"; '
            f'make -j1 '
            f'CC="{cc}" '
            f'CFLAGS="-fPIC -O2 -pedantic -Wall -Wextra -Wno-missing-field-initializers" '
            f'CPPFLAGS="-MMD" '
            f'VCS_IDREV="echo v{self.version}" '
            f'INSTALL=cp INSTALL_PROGRAM=cp INSTALL_DATA=cp',
            cwd=self.source_folder
        )

    def package(self):
        # Binary
        copy(self, "opentyrian", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # License
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Command-line application, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
