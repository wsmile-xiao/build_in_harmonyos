#!/usr/bin/env python3
"""Conan recipe for inifile 1.1-1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class IniFileConan(ConanFile):
    name = "inifile"
    version = "1.1-1"
    description = "Simple INI parser for Lua"
    license = "BSD-2-Clause"
    homepage = "https://github.com/bartbes/inifile"
    url = "https://github.com/bartbes/inifile"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "inifile.lua", src=self.source_folder, dst=lua_share)
        copy(self, "inifile.lua", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

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

