#!/usr/bin/env python3
"""Conan recipe for lua-pc 5.4.7 — Lua interpreter and library for OHOS.

Lua uses a custom Makefile (no configure). The 'linux' target provides
POSIX-compatible build with readline-like features. This recipe builds
both the static library (liblua.a) and the executables (lua, luac).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaPcConan(ConanFile):
    name = "lua-pc"
    version = "5.4.7"
    description = "Lua programming language interpreter and library"
    license = "MIT"
    homepage = "https://www.lua.org"
    url = ""  # CI fills this

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

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # Lua uses 'make linux' target for POSIX-compatible build.
        # MYCFLAGS suppresses warnings treated as errors by clang.
        # R9: Use -j1 (Lua Makefile doesn't support parallel builds well).
        self.run(f"make linux CC={cc} MYCFLAGS=\"-Wno-unused-but-set-variable\" -j1", cwd=self.source_folder)

    def package(self):
        # Copy headers from src/
        copy(self, "lua.h", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "include"))
        copy(self, "luaconf.h", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "include"))
        copy(self, "lualib.h", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "include"))
        copy(self, "lauxlib.h", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "include"))
        copy(self, "lua.hpp", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "include"))

        # Copy static library from src/
        copy(self, "liblua.a", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "lib"))

        # Copy executables from src/
        copy(self, "lua", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "bin"))
        copy(self, "luac", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["lua"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
