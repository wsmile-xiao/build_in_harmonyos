#!/usr/bin/env python3
"""Conan recipe for dkjson 2.8-1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class DkjsonConan(ConanFile):
    name = "dkjson"
    version = "2.8-1"
    description = "David Kolf's pure Lua JSON encoder and decoder"
    license = "MIT/X11"
    homepage = "http://dkolf.de/dkjson-lua/"
    url = "http://dkolf.de/dkjson-lua/"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "dkjson.lua", src=self.source_folder, dst=lua_share)
        copy(self, "readme.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

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

