#!/usr/bin/env python3
"""Test package for luasystem."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LuasystemTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8.1")

    def build(self):
        source = os.path.join(self.recipe_folder, "test_luasystem.c")
        lua = self.dependencies["lua"].cpp_info
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        exe = os.path.join(self.build_folder, "test_luasystem")
        includes = " ".join(f'-I"{path}"' for path in lua.includedirs)
        libdirs = " ".join(f'-L"{path}"' for path in lua.libdirs)
        libs = " ".join(f"-l{name}" for name in lua.libs)
        system_libs = " ".join(f"-l{name}" for name in lua.system_libs)
        self.run(f'"{cc}" "{source}" -o "{exe}" {includes} {libdirs} {libs} {system_libs} -Wl,-E')
        self._exe = exe

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["luasystem"].package_folder
        lua_share = os.path.join(pkg, "share", "lua", "5.4")
        lua_lib = os.path.join(pkg, "lib", "lua", "5.4")
        env = Environment()
        env.define("LUA_PATH", os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;")
        env.define("LUA_CPATH", os.path.join(lua_lib, "?.so") + ";" + os.path.join(lua_lib, "?", "core.so") + ";;")
        with env.vars(self).apply():
            self.run(f'"{self._exe}"')
