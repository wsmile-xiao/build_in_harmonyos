#!/usr/bin/env python3
"""Conan test_package for acf-chrony.

Substantive verification (R34) of the Lua ACF app plugin package:
  1. build() compiles a tiny Lua 5.4 runner (mini_lua.c) against the conan
     lua/5.4.8 static library (headers + liblua.a) — no external download.
     mini_lua.c is a copy of the acf-core test_package runner (same harness).
  2. test() runs test_app.sh which:
       - checks the packaged app plugin layout (controller/model/.lsp/.menu/.roles),
       - loads the REAL chrony-controller module and dispatches its status
         action through a mock model, verifying the controller→model chain
         that acf-core's acf-cli would dispatch at runtime.
"""
import os

from conan import ConanFile


class AcfChronyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lua is a transitive dep of acf-chrony (via acf-core); declare it
        # directly so the test can link the mini_lua runner against its
        # headers + liblua.a.
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
        chrony_pkg = self.dependencies["acf-chrony"]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_app.sh {chrony_pkg.package_folder}", env="conanrun")
