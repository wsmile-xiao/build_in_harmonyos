#!/usr/bin/env python3
"""Test package for lua-mimetypes.

Compiles a C program that embeds Lua, sets package.path to point at
the installed lua-mimetypes package, then verifies mimetypes.guess() API.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LuaMimetypesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8")

    def build(self):
        source = os.path.join(self.recipe_folder, "test_mimetypes.c")
        lua = self.dependencies["lua"]
        lua_pkg = lua.package_folder
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
        exe = os.path.join(self.build_folder, "test_mimetypes")

        inc = os.path.join(lua_pkg, "include")
        lib = os.path.join(lua_pkg, "lib")
        cmd = f'"{cc}" "{source}" -o "{exe}" -I"{inc}" -L"{lib}" -llua -ldl -lm -Wl,-E'
        self.run(cmd)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: compile and link test passed")
            return
        mime_share = os.path.join(
            self.dependencies["lua-mimetypes"].package_folder, "share", "lua", "5.4"
        )
        env = Environment()
        env.define("LUA_PATH", os.path.join(mime_share, "?.lua") + ";;")
        with env.vars(self).apply():
            exe = os.path.join(self.build_folder, "test_mimetypes")
            self.run(f'"{exe}"')
