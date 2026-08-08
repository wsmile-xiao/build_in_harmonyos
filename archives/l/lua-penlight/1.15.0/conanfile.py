#!/usr/bin/env python3
"""Conan recipe for lua-penlight 1.15.0."""

import os

from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class LuaPenlightConan(ConanFile):
    name = "lua-penlight"
    version = "1.15.0"
    description = "Lua utility libraries loosely based on the Python standard libraries"
    license = "MIT/X11"
    homepage = "https://lunarmodules.github.io/Penlight/"
    url = "https://github.com/lunarmodules/Penlight"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("luafilesystem/1.8.0-1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        app_lua = os.path.join(self.source_folder, "lua", "pl", "app.lua")
        with open(app_lua, "r", encoding="utf-8") as handle:
            app_source = handle.read()
        if "OpenHarmony" in app_source:
            return
        replace_in_file(
            self,
            app_lua,
            "        local res = f:read()\n"
            "        if res == 'Darwin' then res = 'OSX' end\n"
            "        f:close()\n"
            "        return res\n",
            "        local res = f:read()\n"
            "        if res == 'Darwin' then res = 'OSX' end\n"
            "        if not res or res == '' or res == 'OHOS' or res == 'OpenHarmony' or res == 'HarmonyOS' then res = 'Linux' end\n"
            "        f:close()\n"
            "        return res\n",
        )

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "*.lua", src=os.path.join(self.source_folder, "lua", "pl"), dst=os.path.join(lua_share, "pl"))
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

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
