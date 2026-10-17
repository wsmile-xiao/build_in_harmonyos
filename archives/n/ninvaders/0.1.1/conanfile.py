#!/usr/bin/env python3
"""Conan recipe — nInvaders 0.1.1 (ncurses space-invaders terminal game).

nInvaders is a classic space invaders clone for the terminal written in C,
built with a plain Makefile and linked against ncurses (wide-character
build, libncursesw.a, provided as a Conan dependency).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NInvadersConan(ConanFile):
    name = "ninvaders"
    version = "0.1.1"
    description = "nInvaders - a classic space invaders clone for ncurses"
    license = "GPL-2.0-or-later"
    homepage = "https://ninvaders.sourceforge.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 钉到 ohpcd 远端的 OHOS 适配版 recipe (c2aee1d9)。
        # conancenter 的 ncurses/6.4 不含 OHOS config.guess patch，
        # 在 HMFS/HMDFS 上会因 "cannot guess build type" 失败；
        # ohpcd 的 recipe 带 0001-port-for-ohos.patch 与 0002-fix-expr-and-umask.patch，
        # 且 ohpcd 已有预编译二进制 (package 21b17f8b)，命中后无需源码构建。
        self.requires("ncurses/6.4#c2aee1d985863d8d1e798e9278c4ce6d")

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: 官方 URL 下载 + sha256 校验（CI 自动添加镜像 fallback，配方内不手写镜像）
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never from shell env vars.
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")

        src = self.source_folder

        # Get ncurses dependency info from the Conan dependency.
        # cpp_info.includedirs/libdirs are package-relative (e.g. "include"),
        # so resolve them against package_folder to absolute paths — the
        # `make -C {src}` working directory won't contain them otherwise.
        dep = self.dependencies["ncurses"]
        cpp_info = dep.cpp_info
        ncurses_inc = os.path.join(dep.package_folder, cpp_info.includedirs[0]) if cpp_info.includedirs else os.path.join(dep.package_folder, "include")
        ncurses_lib = os.path.join(dep.package_folder, cpp_info.libdirs[0]) if cpp_info.libdirs else os.path.join(dep.package_folder, "lib")

        # -fcommon: the 2002-era sources define global arrays directly in the
        # headers; modern clang defaults to -fno-common -> multiple definition
        # errors at link time (verified locally against vendored ncurses.h).
        cflags = f"-O3 -Wall -fcommon -I{ncurses_inc}"
        # The upstream Makefile's default LIBS=-lncurses, but the OHOS
        # wide-character ncurses package produces libncursesw.a only.
        ldflags = f"-L{ncurses_lib}"
        libs = "-lncursesw"

        # Build with the Makefile
        self.run(f"make -C {src} clean", ignore_errors=True)
        self.run(
            f"make -C {src} -j1 V=1 CC={cc} "
            f"CFLAGS='{cflags}' "
            f"LDFLAGS='{ldflags}' "
            f"LIBS='{libs}' "
            f"OPTIONS=''"
        )

    def package(self):
        copy(self, "nInvaders",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "gpl.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]