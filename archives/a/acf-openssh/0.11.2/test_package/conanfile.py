#!/usr/bin/env python3
"""Functional consumer test for acf-openssh 0.11.2."""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class AcfOpensshTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "runner.c", "test.lua", "test_layout.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Direct declarations expose the package folders to this test while
        # resolving to the same dependency nodes as the tested application.
        self.requires("acf-core/0.24.1")
        self.requires("acf-lib-lua5.4/0.11.1")
        self.requires("lua-subprocess/0.02")
        self.requires("luaposix/36.3.1.1")
        self.requires("lua/5.4.8")

    def build(self):
        lua = self.dependencies["lua"]
        include_dir = os.path.join(lua.package_folder, "include")
        lua_lib = os.path.join(lua.package_folder, "lib", "liblua.a")
        runner = os.path.join(self.build_folder, "acf-openssh-test-runner")
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

        app = self.dependencies["acf-openssh"]
        core = self.dependencies["acf-core"]
        acf_lib = self.dependencies["acf-lib-lua5.4"]
        luaposix = self.dependencies["luaposix"]
        subprocess = self.dependencies["lua-subprocess"]

        layout_script = os.path.join(self.source_folder, "test_layout.sh")
        self.run(
            f'sh "{layout_script}" "{app.package_folder}" '
            f'"{core.package_folder}"',
            env="conanrun",
        )

        lua_paths = [
            os.path.join(core.package_folder, "share", "lua", "5.4", "?.lua"),
            os.path.join(core.package_folder, "share", "lua", "5.4", "?", "init.lua"),
            os.path.join(core.package_folder, "share", "acf", "lib", "?.lua"),
            os.path.join(acf_lib.package_folder, "share", "lua", "5.4", "?.lua"),
            os.path.join(acf_lib.package_folder, "share", "lua", "5.4", "?", "init.lua"),
            os.path.join(luaposix.package_folder, "share", "lua", "5.4", "?.lua"),
            os.path.join(luaposix.package_folder, "share", "lua", "5.4", "?", "init.lua"),
        ]
        lua_cpaths = [
            os.path.join(luaposix.package_folder, "lib", "lua", "5.4", "?.so"),
            os.path.join(subprocess.package_folder, "lib", "lua", "5.4", "?.so"),
        ]

        app_dir = os.path.join(
            app.package_folder, "usr", "share", "acf", "app", "openssh"
        )
        config_file = os.path.join(self.build_folder, "sshd_config.test")
        runner = os.path.join(self.build_folder, "acf-openssh-test-runner")
        test_script = os.path.join(self.source_folder, "test.lua")
        command = (
            f'ACF_OPENSSH_CONFIG="{config_file}" '
            f'LUA_PATH="{";".join(lua_paths)};;" '
            f'LUA_CPATH="{";".join(lua_cpaths)};;" '
            f'"{runner}" "{test_script}" "{app_dir}" "{config_file}"'
        )
        self.run(command, env="conanrun")
