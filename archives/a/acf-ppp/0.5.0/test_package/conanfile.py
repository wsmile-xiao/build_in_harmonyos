#!/usr/bin/env python3
"""Consumer test for the packaged acf-ppp Lua application module."""

import os
from pathlib import Path

from conan import ConanFile


class AcfPppTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lua/5.4.8 ships liblua.a and headers, but no interpreter binary.
        # Link a small test-only runner so the functional probe is portable.
        self.requires("lua/5.4.8")

    def build(self):
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        lua_root = self.dependencies["lua"].package_folder
        self.run(
            f'{cc} -o lua-runner mini_lua.c '
            f'-I"{os.path.join(lua_root, "include")}" '
            f'"{os.path.join(lua_root, "lib", "liblua.a")}" -ldl -lm',
            env="conanbuild",
        )

    def test(self):
        package = self.dependencies["acf-ppp"]
        acf_core = self.dependencies["acf-core"]
        script = Path(self.source_folder) / "test_acf_ppp.sh"
        self.run(
            f'sh "{script}" "{package.package_folder}" '
            f'"{acf_core.package_folder}"',
            env="conanrun",
        )
