#!/usr/bin/env python3
"""Conan recipe — open-adventure 1.20 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, chdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpenAdventureConan(ConanFile):
    name = "open-adventure"
    version = "1.20"
    description = "Colossal Cave Adventure — the classic text adventure game"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.com/esr/open-adventure"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libedit/20240808")
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf (two-step dict access, not colon path)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Respect build_type setting
        if self.settings.build_type == "Debug":
            cflags = "-fPIC -g -O0"
        elif self.settings.build_type == "RelWithDebInfo":
            cflags = "-fPIC -g -O2"
        else:
            cflags = "-fPIC -O2"

        pkg_config_path = self.generators_folder
        ncurses_libdir = os.path.join(self.dependencies["ncurses"].package_folder, "lib")
        libedit_libdir = os.path.join(self.dependencies["libedit"].package_folder, "lib")
        ldflags = f"-L{libedit_libdir} -L{ncurses_libdir}"

        # libedit's system_libs declares "tinfo", so PkgConfigDeps generates
        # a .pc file with -ltinfo in Libs. But ncurses widec (--enable-widec)
        # only produces libncursesw.a (no standalone libtinfo.a). Override LIBS
        # to link against libncursesw which provides all terminfo symbols.
        # INC (pkg-config --cflags libedit) still resolves include paths normally.
        # Use -Wl,-Bstatic to force static linking against libedit.a (libedit
        # package ships both .a and .so; without this, the linker prefers .so,
        # creating a dynamic dependency that breaks at runtime on OHOS).
        libs = "-Wl,-Bstatic -ledit -lncursesw -Wl,-Bdynamic"

        with chdir(self, self.source_folder):
            self.run(f'PKG_CONFIG_PATH="{pkg_config_path}" LDFLAGS="{ldflags}" make CC={cc} CFLAGS="{cflags}" LIBS="{libs}" -j1', env="conanbuild")
            self.run(f'PKG_CONFIG_PATH="{pkg_config_path}" LDFLAGS="{ldflags}" make cheat CC={cc} CFLAGS="{cflags}" LIBS="{libs}"', env="conanbuild")

    def package(self):
        copy(self, "advent", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cheat", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
