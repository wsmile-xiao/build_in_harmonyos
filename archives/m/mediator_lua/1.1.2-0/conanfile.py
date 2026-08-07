#!/usr/bin/env python3
"""Conan recipe for mediator_lua 1.1.2-0."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MediatorLuaConan(ConanFile):
    name = "mediator_lua"
    version = "1.1.2-0"
    description = "Pure Lua event mediator used by Busted"
    license = "MIT"
    homepage = "http://olivinelabs.com/mediator_lua/"
    url = "https://github.com/Olivine-Labs/mediator_lua"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "mediator.lua", src=os.path.join(self.source_folder, "src"), dst=lua_share)
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

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

