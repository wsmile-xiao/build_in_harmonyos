#!/usr/bin/env python3
"""Conan recipe for lua-struct 0.9.2 — Pure Lua binary packing/unpacking library."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LuaStructConan(ConanFile):
    name = "lua-struct"
    version = "0.9.2"
    description = "Implementation of binary packing/unpacking in pure Lua"
    license = "MIT/X11"
    homepage = "https://github.com/iryont/lua-struct"
    url = "https://github.com/iryont/lua-struct"
    topics = ("lua", "binary", "pack", "unpack")

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "struct.lua", src=os.path.join(self.source_folder, "src"), dst=lua_share)
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";;",
        )
