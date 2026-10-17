#!/usr/bin/env python3
"""Conan test_package — awall 1.14.0 L1 smoke test.

awall is a pure Lua CLI tool whose shebang (#!/usr/bin/lua) does not exist on
OHOS, so the test invokes the interpreter explicitly via the lua/5.5.0 conan
dependency (resolved from the dependency graph, never hardcoded).

The test performs three layers of verification:
  1. Structural gate (mandatory): awall CLI present/executable, Lua modules
     and policy JSON templates installed per the upstream Makefile layout.
  2. Syntax gate (mandatory): every packaged .lua file is parsed with the
     lua interpreter (`assert(loadfile(...))`) — real interpreter involvement,
     no host Lua modules required.
  3. Best-effort run: when the host Lua helper modules (luaposix is provided
     as a test dependency; alt_getopt/lpc/stringy/cjson are host-env deps not
     published to ohpcd) are reachable, `awall list` / `awall translate` are
     really executed and their output checked; otherwise the SKIP reason is
     reported explicitly (never silently reported as "passed run").
"""
import os

from conan import ConanFile


class AwallTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lua interpreter + posix module come from published ohpcd packages;
        # declared as direct test deps so the conanrun env provides them.
        self.requires("lua/5.5.0")
        self.requires("luaposix/36.3")

    def test(self):
        pkg = self.dependencies["awall"]
        lua = self.dependencies["lua"]
        posix = self.dependencies["luaposix"]

        pkg_folder = pkg.package_folder
        lua_bin = os.path.join(lua.package_folder, "bin", "lua")
        posix_share = os.path.join(posix.package_folder, "share", "lua", "5.5")
        posix_lib = os.path.join(posix.package_folder, "lib", "lua", "5.5")
        pkg_lua = os.path.join(pkg_folder, "usr", "share", "lua", "5.5")

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # LUA_PATH/LUA_CPATH: package's own awall modules first, then luaposix.
        lua_path = (f"{pkg_lua}/?.lua;{pkg_lua}/?/init.lua;"
                    f"{posix_share}/?.lua;{posix_share}/?/init.lua")
        lua_cpath = f"{posix_lib}/?.so;{posix_lib}/?/init.so"
        env_cmd = (f'LUA_BIN="{lua_bin}" LUA_PATH="{lua_path}" '
                   f'LUA_CPATH="{lua_cpath}"')
        self.run(f'{env_cmd} {bash} test.sh "{pkg_folder}"', env="conanrun")
