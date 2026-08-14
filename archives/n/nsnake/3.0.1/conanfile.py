#!/usr/bin/env python3
"""Conan recipe — nsnake 3.0.1 (ncurses snake game).

nsnake is a classic snake game on the terminal using ncurses. Upstream uses
a plain Makefile (not autotools). ncurses is provided as a Conan dependency.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NsnakeConan(ConanFile):
    name = "nsnake"
    version = "3.0.1"
    description = "nsnake - classic snake game on the terminal using ncurses"
    license = "GPL-3.0"
    homepage = "https://github.com/alexdantas/nSnake"
    url = "https://github.com/alexdantas/nSnake"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: 官方 URL 下载 + sha256 校验（CI 自动添加镜像 fallback，配方内不手写镜像）
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")
        cxx = ce.get("cpp", "clang++")

        src = self.source_folder

        # Get ncurses dependency info from the Conan dependency
        dep = self.dependencies["ncurses"]
        cpp_info = dep.cpp_info
        ncurses_inc = ":".join(cpp_info.includedirs) if cpp_info.includedirs else os.path.join(dep.package_folder, "include")
        ncurses_lib = ":".join(cpp_info.libdirs) if cpp_info.libdirs else os.path.join(dep.package_folder, "lib")
        ncurses_libs = " ".join(f"-l{lib}" for lib in cpp_info.libs)

        cxxflags = f"-O2 -Wall -Wextra -I{ncurses_inc}"
        # Override LDFLAGS entirely (the Makefile's default LDFLAGS has
        # -lncurses, but the wide-character build produces libncursesw.a).
        ldflags = f"-L{ncurses_lib} {ncurses_libs}"

        # Build with the Makefile
        self.run(
            f"make -C {src} clean", ignore_errors=True
        )
        self.run(
            f"make -C {src} -j1 V=1 CC={cc} CXX={cxx} "
            f"CXXFLAGS='{cxxflags}' "
            f"CFLAGS_PLATFORM='-I{ncurses_inc}' "
            f"LDFLAGS='{ldflags}' "
            f"PREFIX=/usr"
        )

    def package(self):
        copy(self, "nsnake",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]