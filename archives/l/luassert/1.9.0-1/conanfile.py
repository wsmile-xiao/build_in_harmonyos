#!/usr/bin/env python3
"""Conan recipe for luassert 1.9.0-1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuassertConan(ConanFile):
    name = "luassert"
    version = "1.9.0-1"
    description = "Lua assertions extension"
    license = "MIT"
    homepage = "https://lunarmodules.github.io/busted/"
    url = "https://github.com/lunarmodules/luassert"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("lua-say/1.4.1-3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4", "luassert")
        copy(self, "*.lua", src=os.path.join(self.source_folder, "src"), dst=lua_share)
        copy(self, "*.lua", src=os.path.join(self.source_folder, "src", "matchers"), dst=os.path.join(lua_share, "matchers"))
        copy(self, "*.lua", src=os.path.join(self.source_folder, "src", "formatters"), dst=os.path.join(lua_share, "formatters"))
        copy(self, "*.lua", src=os.path.join(self.source_folder, "src", "languages"), dst=os.path.join(lua_share, "languages"))
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

