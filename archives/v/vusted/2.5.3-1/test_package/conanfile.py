#!/usr/bin/env python3
"""Test package for vusted."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class VustedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    lua_path_deps = (
        "vusted",
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

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("neovim/0.11.3")
        self.requires("busted/2.2.0-1")
        self.requires("lua_cliargs/3.0.2-1")
        self.requires("luasystem/0.6.3-1")
        self.requires("dkjson/2.8-1")
        self.requires("lua-say/1.4.1-3")
        self.requires("luassert/1.9.0-1")
        self.requires("lua-term/0.7")
        self.requires("lua-penlight/1.15.0")
        self.requires("mediator_lua/1.1.2-0")

    def _lua_path(self):
        paths = []
        for dep_name in self.lua_path_deps:
            pkg = self.dependencies[dep_name].package_folder
            lua_share = os.path.join(pkg, "share", "lua", "5.4")
            paths.extend([os.path.join(lua_share, "?.lua"), os.path.join(lua_share, "?", "init.lua")])
        return ";".join(paths) + ";;"

    def test(self):
        check = os.path.join(self.recipe_folder, "check_smoke_spec.py")
        spec = os.path.join(self.recipe_folder, "smoke_spec.lua")
        self.run(f'"{sys.executable}" "{check}" "{spec}"')
        if not can_run(self):
            return
        nvim = os.path.join(self.dependencies["neovim"].package_folder, "bin", "nvim")
        test_root = os.path.join(self.build_folder, "vusted-test-env")
        test_tmp = os.path.join(test_root, "tmp")
        test_home = os.path.join(test_root, "home")
        xdg_runtime = os.path.join(test_root, "xdg-runtime")
        xdg_cache = os.path.join(test_home, ".cache")
        xdg_config = os.path.join(test_home, ".config")
        xdg_data = os.path.join(test_home, ".local", "share")
        xdg_state = os.path.join(test_home, ".local", "state")
        for path in (
            test_tmp,
            test_home,
            xdg_cache,
            xdg_config,
            xdg_data,
            xdg_state,
            xdg_runtime,
        ):
            os.makedirs(path, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)

        env = Environment()
        env.prepend_path("PATH", os.path.join(self.dependencies["vusted"].package_folder, "bin"))
        env.prepend_path("PATH", os.path.join(self.dependencies["neovim"].package_folder, "bin"))
        env.define("LUA_PATH", self._lua_path())
        env.define("LUA_CPATH", "")
        env.define("HOME", test_home)
        env.define("TMPDIR", test_tmp)
        env.define("TMP", test_tmp)
        env.define("TEMP", test_tmp)
        env.define("XDG_CACHE_HOME", xdg_cache)
        env.define("XDG_CONFIG_HOME", xdg_config)
        env.define("XDG_DATA_HOME", xdg_data)
        env.define("XDG_STATE_HOME", xdg_state)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("VUSTED_SMOKE_TMP", test_tmp)
        env.define("VUSTED_NVIM", nvim)
        env.define("VUSTED_ARGS", "--headless --clean -u NONE -i NONE")
        with env.vars(self).apply():
            self.run(f'vusted "{spec}"')
