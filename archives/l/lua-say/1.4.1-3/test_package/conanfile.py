#!/usr/bin/env python3
"""Test package for lua-say."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LuaSayTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8")

    def build(self):
        source = os.path.join(self.recipe_folder, "test_lua_say.c")
        lua = self.dependencies["lua"].cpp_info
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        exe = os.path.join(self.build_folder, "test_lua_say")
        if str(self.settings.os) == "Windows":
            exe += ".exe"
        includes = " ".join(f'-I"{path}"' for path in lua.includedirs)
        libdirs = " ".join(f'-L"{path}"' for path in lua.libdirs)
        libs = " ".join(f"-l{name}" for name in lua.libs)
        system_libs = " ".join(f"-l{name}" for name in lua.system_libs)
        self.run(f'"{cc}" "{source}" -o "{exe}" {includes} {libdirs} {libs} {system_libs}')
        self._exe = exe

    def test(self):
        if not can_run(self):
            return
        say_pkg = self.dependencies["lua-say"].package_folder
        lua_share = os.path.join(say_pkg, "share", "lua", "5.4")
        env = Environment()
        env.define("LUA_PATH", os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;")
        with env.vars(self).apply():
            self.run(f'"{self._exe}"')
