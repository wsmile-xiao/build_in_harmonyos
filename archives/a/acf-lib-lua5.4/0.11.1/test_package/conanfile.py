#!/usr/bin/env python3
"""Conan test_package for acf-lib-lua5.4.

Substantive verification (R34) of the pure-Lua library package:
  1. build() compiles a tiny Lua 5.4 runner (mini_lua.c) against the conan
     lua/5.4.8 static library (headers + liblua.a) — no external download.
  2. test() runs test_acf_lib.sh which:
        - checks the packaged layout (share/lua/5.4/acf/*.lua + compat
          symlinks),
        - loads each REAL acf.* module (format/fs/html/date/db/processinfo/
          validator/apk) and exercises the pure-Lua portions of its API,
        - uses test-harness stub modules (posix/subprocess/luasql.*) so the
          pure-Lua code paths of acf.format / acf.validator run end-to-end
          even though the external Lua deps are not yet packaged for Lua 5.4.
"""
import os

from conan import ConanFile


class AcfLibLua54TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lua is a transitive dep of acf-lib-lua5.4; declare it directly so the
        # test can link the mini_lua runner against its headers + liblua.a.
        self.requires("lua/5.4.8")

    def build(self):
        # R33: compiler from Conan conf, never from bare shell env vars
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        lua_pkg = self.dependencies["lua"]
        lua_root = lua_pkg.package_folder
        self.run(
            f"{cc} -o lua-runner mini_lua.c "
            f"-I{os.path.join(lua_root, 'include')} "
            f"{os.path.join(lua_root, 'lib', 'liblua.a')} -ldl -lm",
            env="conanbuild")

    def test(self):
        acf_pkg = self.dependencies["acf-lib-lua5.4"]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_acf_lib.sh {acf_pkg.package_folder}", env="conanrun")
