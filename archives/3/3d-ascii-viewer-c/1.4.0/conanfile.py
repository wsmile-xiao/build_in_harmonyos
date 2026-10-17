#!/usr/bin/env python3
"""Conan recipe for 3d-ascii-viewer-c 1.4.0 — terminal ASCII 3D model viewer (raw Makefile).

Build: make && install binary to bin/. Depends on ncurses (uses -lncursesw from the
published ncurses/6.4 package). Produces the `3d-ascii-viewer` CLI executable.
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ThreeDAsciiViewerCConan(ConanFile):
    name = "3d-ascii-viewer-c"
    version = "1.4.0"
    description = "3d-ascii-viewer-c — view 3D models (.obj/.stl) as ASCII art in the terminal"
    license = "MIT"
    homepage = "https://github.com/autopawn/3d-ascii-viewer-c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # ncurses provided via conan dependency
        dep = self.dependencies["ncurses"]
        include_dirs = os.pathsep.join(dep.cpp_info.includedirs)
        lib_dirs = os.pathsep.join(dep.cpp_info.libdirs)

        # R9: always -j1; pass CC/CFLAGS/LDFLAGS explicitly (Makefile defaults to gcc)
        self.run(
            f"make CC={cc} CFLAGS='-Wall -fPIC -O2 -I\"{include_dirs}\"' "
            f"LDFLAGS='-L\"{lib_dirs}\" -lm -lncursesw' -j1",
            cwd=self.source_folder)

    def package(self):
        # Distribute CLI binary + sample models
        copy(self, "3d-ascii-viewer", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*", os.path.join(self.source_folder, "models"),
             os.path.join(self.package_folder, "share", "3d-ascii-viewer-c", "models"))

    def package_info(self):
        # R38: CLI tool → bindirs only
        self.cpp_info.bindirs = ["bin"]