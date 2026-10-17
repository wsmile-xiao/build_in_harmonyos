#!/usr/bin/env python3
"""Conan test_package for acf-core.

Substantive verification (R34) of the Lua framework package:
  1. build() compiles a tiny Lua 5.4 runner (mini_lua.c) against the conan
     lua/5.4.8 static library (headers + liblua.a) — no external download.
  2. test() runs test_acf_core.sh which:
       - checks the packaged layout (bin/, share/lua/5.4/acf, share/acf/*),
       - loads the REAL acf.mvc module and dispatches a controller action
         (acf-util/welcome/read) using pure-Lua test-harness modules for the
         external Lua deps (posix/subprocess) not yet available as conan
         packages for Lua 5.4,
       - verifies acfpasswd/acf-cli CLI behavior.
"""
import os

from conan import ConanFile


class AcfCoreTestConan(ConanFile):
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
        acf_pkg = self.dependencies["acf-core"]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_acf_core.sh {acf_pkg.package_folder}", env="conanrun")
