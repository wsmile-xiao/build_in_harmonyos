#!/usr/bin/env python3
"""Conan recipe for lua-subprocess 0.02 — a Lua C extension module
that provides subprocess spawning and I/O management.

Build: compiles subprocess.c + liolib-copy.c into subprocess.so (shared Lua C module).
The .so is NOT linked against liblua.a — Lua symbols are resolved at runtime
via dlopen when the Lua interpreter loads the module.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaSubprocessConan(ConanFile):
    name = "lua-subprocess"
    version = "0.02"
    description = "Lua module for spawning subprocesses and managing I/O"
    license = "MIT"
    homepage = "https://github.com/xlq/lua-subprocess"

    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")

        # Get lua include dir from the dependency's package folder
        lua = self.dependencies["lua"]
        lua_include = os.path.join(lua.package_folder, "include")

        optimize = "-O2" if self.settings.build_type == "Release" else "-O0 -g"
        src = self.source_folder

        # Build subprocess.so as a shared Lua C module.
        # NOT linked against liblua.a — symbols resolved at runtime via dlopen.
        self.run(
            f'"{cc}" -Wall -Wextra -pedantic {optimize} '
            f'-I"{lua_include}" '
            f'-DOS_POSIX -shared -fPIC '
            f'-o "{src}/subprocess.so" '
            f'"{src}/subprocess.c" "{src}/liolib-copy.c"'
        )

    def package(self):
        # Install subprocess.so to lib/lua/5.4/ (standard Lua C module path)
        copy(
            self,
            "subprocess.so",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib", "lua", "5.4"),
        )

    def package_info(self):
        self.cpp_info.libs = ["subprocess"]
        self.cpp_info.libdirs = ["lib/lua/5.4"]
        self.cpp_info.requires = ["lua::lua"]
