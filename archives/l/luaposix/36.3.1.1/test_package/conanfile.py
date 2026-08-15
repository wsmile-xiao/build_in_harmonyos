#!/usr/bin/env python3
"""Consumer test for the Lua 5.4 luaposix package."""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class LuaposixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "runner.c", "test.lua"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.8")

    def build(self):
        lua = self.dependencies["lua"]
        include_dir = os.path.join(lua.package_folder, "include")
        lua_lib = os.path.join(lua.package_folder, "lib", "liblua.a")
        runner = os.path.join(self.build_folder, "luaposix-test-runner")
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        self.run(
            f'{cc} "{os.path.join(self.source_folder, "runner.c")}" '
            f'-I"{include_dir}" "{lua_lib}" -ldl -lm '
            f'-Wl,--export-dynamic -o "{runner}"',
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            return
        runner = os.path.join(self.build_folder, "luaposix-test-runner")
        script = os.path.join(self.source_folder, "test.lua")
        self.run(
            f'"{runner}" "{script}"',
            env="conanrun",
        )
