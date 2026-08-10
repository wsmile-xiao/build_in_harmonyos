#!/usr/bin/env python3
"""Conan recipe for lua-tableshape 2.7.0 — pure Lua table shape validation library."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuaTableshapeConan(ConanFile):
    name = "lua-tableshape"
    version = "2.7.0"
    description = "Test the shape or structure of a Lua table"
    license = "MIT"
    homepage = "https://github.com/leafo/tableshape"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure Lua library — no compilation step needed.
        # The release tarball ships pre-compiled .lua files.
        pass

    def package(self):
        # Install Lua modules to res/share/lua/5.4/tableshape/ so that
        # require("tableshape") resolves via package.path "?/init.lua"
        lua_dir = os.path.join(self.package_folder, "res", "share", "lua", "5.4")
        copy(self, "*.lua", src=os.path.join(self.source_folder, "tableshape"),
             dst=os.path.join(lua_dir, "tableshape"))
        # License (MIT — text is in README.md, no separate LICENSE file)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        lua_dir = os.path.join(self.package_folder, "res", "share", "lua", "5.4")
        self.runenv_info.prepend_path(
            "LUA_PATH",
            os.path.join(lua_dir, "?.lua") + ";" + os.path.join(lua_dir, "?", "init.lua"),
        )
