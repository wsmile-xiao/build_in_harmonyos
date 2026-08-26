#!/usr/bin/env python3
"""Conan recipe — lua-ansicolors 1.0.2 (custom).

Pure Lua library — no compilation required.
The package copies ansicolors.lua into share/lua/5.4/.
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LuaAnsiColorsConan(ConanFile):
    name = "lua-ansicolors"
    version = "1.0.2"
    description = "ANSI terminal color manipulation library for Lua"
    license = "MIT"
    homepage = "https://github.com/kikito/ansicolors.lua"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure Lua library — no compilation step needed.
        apply_conandata_patches(self)

    def package(self):
        lua_dir = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "ansicolors.lua", src=self.source_folder, dst=lua_dir)
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;",
        )
