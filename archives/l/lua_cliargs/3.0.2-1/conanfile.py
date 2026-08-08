#!/usr/bin/env python3
"""Conan recipe for lua_cliargs 3.0.2-1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuaCliargsConan(ConanFile):
    name = "lua_cliargs"
    version = "3.0.2-1"
    description = "Pure Lua command-line argument parser"
    license = "MIT"
    homepage = "https://github.com/lunarmodules/lua_cliargs"
    url = "https://github.com/lunarmodules/lua_cliargs"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("inifile/1.1-1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "*.lua", src=os.path.join(self.source_folder, "src"), dst=lua_share)
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
