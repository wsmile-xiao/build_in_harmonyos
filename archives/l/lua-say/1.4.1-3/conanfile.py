#!/usr/bin/env python3
"""Conan recipe for lua-say 1.4.1-3."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuaSayConan(ConanFile):
    name = "lua-say"
    version = "1.4.1-3"
    description = "Lua string key/value store used by Busted and Luassert"
    license = "MIT"
    homepage = "https://github.com/lunarmodules/say"
    url = "https://github.com/lunarmodules/say"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_dir = os.path.join(self.package_folder, "share", "lua", "5.4", "say")
        copy(self, "*.lua", src=os.path.join(self.source_folder, "src", "say"), dst=lua_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

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
