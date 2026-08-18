#!/usr/bin/env python3
"""Conan recipe for lua-sqlite 2.6.0 — SQLite3 driver for LuaSQL.

LuaSQL provides database connectivity for Lua. This recipe builds the
SQLite3 driver as a shared object (sqlite3.so) loaded by Lua at runtime
via require("luasql.sqlite3"). Lua headers are needed at compile time;
sqlite3 is linked statically into the .so. Lua symbols remain undefined
and are resolved at runtime by the host Lua interpreter.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaSqliteConan(ConanFile):
    name = "lua-sqlite"
    version = "2.6.0"
    description = "SQLite3 driver for LuaSQL — database connectivity for Lua"
    license = "MIT"
    homepage = "https://lunarmodules.github.io/luasql/"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Get dependency paths from Conan (R33: no shell env vars for compiler)
        lua_info = self.dependencies["lua"]
        sqlite3_info = self.dependencies["sqlite3"]

        lua_inc = lua_info.cpp_info.includedirs[0]
        sqlite3_inc = sqlite3_info.cpp_info.includedirs[0]
        sqlite3_lib = sqlite3_info.cpp_info.libdirs[0]

        # R33: Get compiler from Conan settings, never from shell env vars
        cc = str(self.settings.compiler)
        config_shell = os.environ.get("CONFIG_SHELL", "bash")

        # Build sqlite3 driver — all paths via make variables, no patches needed.
        # Lua is NOT linked (-llua omitted): symbols resolved at runtime by host interpreter.
        # sqlite3 is linked statically into the .so.
        self.run(
            f'{config_shell} -c "'
            f'cd {self.source_folder} && '
            f"make sqlite3 CC={cc} "
            f"LUA_INC={lua_inc} "
            f"DRIVER_INCS_sqlite3=-I{sqlite3_inc} "
            f"DRIVER_LIBS_sqlite3='-L{sqlite3_lib} -lsqlite3' "
            f'LIB_OPTION=-shared -j1"'
        )

    def package(self):
        # Install .so to lib/luasql/ for require("luasql.sqlite3")
        copy(self, "sqlite3.so",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "lib", "luasql"))

    def package_info(self):
        self.cpp_info.libs = ["sqlite3"]
