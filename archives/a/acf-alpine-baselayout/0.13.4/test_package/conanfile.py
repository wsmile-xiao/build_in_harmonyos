#!/usr/bin/env python3
"""Conan test_package — acf-alpine-baselayout 0.13.4.

L1 official test: substantive consumer verification (R34) of the packaged
pure-Lua ACF application module:

  1. build() compiles a tiny Lua 5.4 runner (mini_lua.c) against the conan
     lua/5.4.8 static library (headers + liblua.a) — no external download.
  2. test() runs test_acf_alpine_baselayout.sh which:
       - checks the packaged layout under usr/share/acf/app/alpine-baselayout
         (controllers, models, .lsp views, .menu, .roles — 46 files + 9 symlinks),
       - validates the .roles content (GUEST/USER/EDITOR/EXPERT/ADMIN roles),
       - syntax-loads every packaged .lua file with the REAL Lua 5.4 runtime
         (lua-runner test_syntax.lua → loadfile() on each file),
       - verifies the package does NOT accidentally expose lib/bin artifacts.
"""
import os

from conan import ConanFile


class AcfAlpineBaselayoutTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lua is a transitive dep of acf-core; declare it directly so the test
        # can link the mini_lua runner against its headers + liblua.a.
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
        abl_pkg = self.dependencies["acf-alpine-baselayout"]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f"{bash} test_acf_alpine_baselayout.sh "
            f"{abl_pkg.package_folder} {os.getcwd()}",
            env="conanrun")
