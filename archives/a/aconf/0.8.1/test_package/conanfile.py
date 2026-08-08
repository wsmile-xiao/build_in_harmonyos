#!/usr/bin/env python3
"""Conan test_package for aconf 0.8.1.

L1 test: verify the aconfd launcher script is installed/executable and the
core Lua module parses. aconf is a Lua/shell daemon package, so test.c uses
only standard C and invokes aconfd/lua via system().
"""
import os

from conan import ConanFile


class AconfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(f"{cc} test.c -o test_aconf")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap
        # binary execution with bash.
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in (
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/bin/bash",
            ) if os.path.exists(p)),
            "bash",
        )
        pkg_folder = self.dependencies["aconf"].package_folder
        aconf_bin = os.path.join(pkg_folder, "bin")
        aconf_lua = os.path.join(pkg_folder, "usr", "share", "lua", "5.4", "aconf")
        self.run(
            f"PATH={aconf_bin}:$PATH ACONF_LUA_DIR='{aconf_lua}' "
            f"{bash} -c './test_aconf'",
            env="conanrun",
        )
