#!/usr/bin/env python3
"""Conan recipe for luacov 0.16.0-1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuaCovConan(ConanFile):
    name = "luacov"
    version = "0.16.0-1"
    description = "Coverage analysis tool for Lua scripts"
    license = "MIT"
    homepage = "https://lunarmodules.github.io/luacov/"
    url = "https://github.com/lunarmodules/luacov"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("datafile/0.11-1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "luacov.lua", src=os.path.join(self.source_folder, "src"), dst=lua_share)
        copy(
            self,
            "*.lua",
            src=os.path.join(self.source_folder, "src", "luacov"),
            dst=os.path.join(lua_share, "luacov"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "src", "luacov", "reporter", "html", "static"),
            dst=os.path.join(lua_share, "luacov", "reporter", "html", "static"),
        )
        copy(self, "luacov", src=os.path.join(self.source_folder, "src", "bin"), dst=bin_dir)
        command = os.path.join(bin_dir, "luacov")
        if os.path.exists(command):
            os.chmod(command, 0o755)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        bin_dir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;",
        )

