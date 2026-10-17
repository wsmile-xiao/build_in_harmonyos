#!/usr/bin/env python3
"""Conan test_package for lua-sqlite 2.6.0.

Tests that the sqlite3.so Lua extension module can be loaded by a Lua
interpreter and that basic SQLite3 operations work (create table, insert,
select). A minimal Lua interpreter is compiled from the Conan lua/5.4.8
static library.

R34: The test calls luasql.sqlite3's actual API (connect, execute, fetch).
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class LuaSqliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8")

    def build(self):
        # Get lua dependency info for compiling a minimal interpreter
        lua_info = self.dependencies["lua"]
        lua_inc = lua_info.cpp_info.includedirs[0]
        lua_lib = lua_info.cpp_info.libdirs[0]

        # R33: Get compiler from Conan settings
        cc = str(self.settings.compiler)
        # Compile minimal Lua interpreter from conan lua static library.
        # -Wl,-E exports all symbols so the .so module can resolve lua_*
        # at runtime (required for Lua extension module loading).
        src = os.path.join(self.source_folder, "min_lua.c")
        self.run(
            f"{cc} -o lua_test {src} "
            f"-I{lua_inc} -L{lua_lib} -llua -lm -ldl "
            f"-Wl,-E -fPIC -O2"
        )

    def test(self):
        # Get lua-sqlite package info
        dep = self.dependencies[self.tested_reference_str]
        lib_dir = dep.cpp_info.libdirs[0]  # path to lib/

        lua_bin = os.path.join(self.build_folder, "lua_test")
        test_script = os.path.join(self.source_folder, "test.lua")

        # LUA_CPATH must point to lib/ so require("luasql.sqlite3")
        # finds lib/luasql/sqlite3.so
        self.run(f"LUA_CPATH={lib_dir}/?.so {lua_bin} {test_script}")
