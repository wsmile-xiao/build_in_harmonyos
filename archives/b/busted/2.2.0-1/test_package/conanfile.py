#!/usr/bin/env python3
"""Test package for busted."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class BustedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    lua_path_deps = (
        "busted",
        "lua_cliargs",
        "luasystem",
        "dkjson",
        "lua-say",
        "luassert",
        "lua-term",
        "lua-penlight",
        "mediator_lua",
    )
    lua_cpath_deps = ("luasystem", "lua-term", "luafilesystem")

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8.1")
        self.requires("lua_cliargs/3.0.2-1")
        self.requires("luasystem/0.6.3-1")
        self.requires("dkjson/2.8-1")
        self.requires("lua-say/1.4.1-3")
        self.requires("luassert/1.9.0-1")
        self.requires("lua-term/0.7")
        self.requires("lua-penlight/1.15.0")
        self.requires("mediator_lua/1.1.2-0")
        self.requires("luafilesystem/1.8.0-1")

    def build(self):
        source = os.path.join(self.recipe_folder, "test_busted.c")
        lua = self.dependencies["lua"].cpp_info
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        exe = os.path.join(self.build_folder, "test_busted")
        includes = " ".join(f'-I"{path}"' for path in lua.includedirs)
        libdirs = " ".join(f'-L"{path}"' for path in lua.libdirs)
        libs = " ".join(f"-l{name}" for name in lua.libs)
        system_libs = " ".join(f"-l{name}" for name in lua.system_libs)
        self.run(f'"{cc}" "{source}" -o "{exe}" {includes} {libdirs} {libs} {system_libs} -Wl,-E')
        self._exe = exe

    def _lua_path(self):
        paths = []
        for dep_name in self.lua_path_deps:
            pkg = self.dependencies[dep_name].package_folder
            lua_share = os.path.join(pkg, "share", "lua", "5.4")
            paths.extend([os.path.join(lua_share, "?.lua"), os.path.join(lua_share, "?", "init.lua")])
        return ";".join(paths) + ";;"

    def _lua_cpath(self):
        paths = []
        for dep_name in self.lua_cpath_deps:
            pkg = self.dependencies[dep_name].package_folder
            lua_lib = os.path.join(pkg, "lib", "lua", "5.4")
            paths.extend([os.path.join(lua_lib, "?.so"), os.path.join(lua_lib, "?", "core.so")])
        return ";".join(paths) + ";;"

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        env.define("LUA_PATH", self._lua_path())
        env.define("LUA_CPATH", self._lua_cpath())
        env.define("BUSTED_LUA", os.path.join(self.dependencies["lua"].package_folder, "bin", "lua"))
        with env.vars(self).apply():
            self.run(f'"{self._exe}"')
            busted = os.path.join(self.dependencies["busted"].package_folder, "bin", "busted")
            smoke = os.path.join(self.recipe_folder, "smoke_spec.lua")
            # Version metadata is already covered by the C smoke above.
            self.run(f'"{busted}" --loaders lua --output plainTerminal "{smoke}"')
