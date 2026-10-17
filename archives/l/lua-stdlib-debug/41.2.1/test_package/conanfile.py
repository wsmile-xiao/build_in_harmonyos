#!/usr/bin/env python3
"""Test package for lua-stdlib-debug — verifies std.debug module loads."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LuaStdlibDebugTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lua-pc provides the lua interpreter to run the test
        self.requires("lua-pc/5.4.7")

    def build(self):
        pass

    def test(self):
        if not can_run(self):
            return

        # Get the lua-stdlib-debug share directory
        debug_pkg = self.dependencies["lua-stdlib-debug"]
        lua_share = os.path.join(debug_pkg.package_folder, "usr", "local", "share", "lua", "5.4")

        # Get the lua interpreter from lua-pc
        lua_pc = self.dependencies["lua-pc"]
        lua_bin = os.path.join(lua_pc.cpp_info.bindirs[0], "lua")

        # Set LUA_PATH so lua can find std.debug
        lua_path = os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;"

        test_script = os.path.join(self.recipe_folder, "test.lua")

        env = Environment()
        env.define("LUA_PATH", lua_path)
        with env.vars(self).apply():
            self.run(f'"{lua_bin}" "{test_script}"')
