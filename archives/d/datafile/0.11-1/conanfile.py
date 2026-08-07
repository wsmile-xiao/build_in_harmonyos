#!/usr/bin/env python3
"""Conan recipe for datafile 0.11-1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class DatafileConan(ConanFile):
    name = "datafile"
    version = "0.11-1"
    description = "Pure Lua helpers for locating data files"
    license = "MIT/X11"
    homepage = "https://github.com/hishamhm/datafile"
    url = "https://github.com/hishamhm/datafile"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "datafile.lua", src=self.source_folder, dst=lua_share)
        copy(
            self,
            "*.lua",
            src=os.path.join(self.source_folder, "datafile"),
            dst=os.path.join(lua_share, "datafile"),
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

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

