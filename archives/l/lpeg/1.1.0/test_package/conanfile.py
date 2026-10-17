#!/usr/bin/env python3
"""Conan test_package for lpeg 1.1.0.

Tests that lpeg.so can be loaded by Lua and that its pattern matching API
works correctly. Since Lua is not published as a Conan recipe, we download
and build Lua from source to run the test.

R34: The test calls lpeg's actual API (P, R, S, match, etc.)
"""
import os

from conan import ConanFile
from conan.tools.files import get


class LpegTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    # Lua source for the test interpreter
    _LUA_URL = "https://www.lua.org/ftp/lua-5.4.7.tar.gz"
    _LUA_SHA256 = "9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Download and build Lua interpreter for testing
        lua_build_dir = os.path.join(self.build_folder, "lua-build")
        get(self, url=self._LUA_URL, sha256=self._LUA_SHA256,
            destination=lua_build_dir, strip_root=False)

        # Get compiler from Conan settings (R33)
        cc = str(self.settings.compiler)
        config_shell = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{config_shell} -c \"cd {lua_build_dir}/lua-5.4.7 && make linux CC={cc} MYCFLAGS='-fPIC -O2' -j1\"")

    def test(self):
        # Get lpeg.so path from the built package
        dep = self.dependencies[self.tested_reference_str]
        lpeg_lib_dir = dep.cpp_info.libdirs[0]

        lua_bin = os.path.join(self.build_folder, "lua-build", "lua-5.4.7", "src", "lua")
        test_script = os.path.join(self.source_folder, "test.lua")

        # Use inline env vars for reliable passing
        self.run(f"LUA_CPATH={lpeg_lib_dir}/?.so {lua_bin} {test_script}")
