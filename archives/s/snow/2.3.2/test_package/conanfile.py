#!/usr/bin/env python3
"""Consumer test for the snow/2.3.2 header-only C library."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class SnowTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "No C compiler configured: set "
                "tools.build:compiler_executables in the Conan profile."
            )

        dependency = self.dependencies["snow"]
        include_dir = os.path.join(dependency.package_folder, "include")
        for test_name in ("test_snow", "test_tmpdir"):
            source = os.path.join(self.source_folder, f"{test_name}.c")
            executable = os.path.join(self.build_folder, test_name)
            self.run(
                f'"{cc}" -std=gnu11 -Wall -Wextra -Wpedantic -Werror '
                f'-I"{include_dir}" "{source}" -o "{executable}"',
                cwd=self.build_folder,
            )

    def test(self):
        if cross_building(self):
            self.output.info(
                "Cross-compiling: the Snow consumer was compiled but cannot run on the host"
            )
            return
        executable = os.path.join(self.build_folder, "test_snow")
        self.run(
            f'"{executable}" --no-color --no-timer --no-maybes',
            env="conanrun",
        )

        tmpdir_test = os.path.join(self.build_folder, "test_tmpdir")
        env = Environment()
        env.define("TMPDIR", "/data/local/tmp")
        env.define(
            "SNOW_EXPECTED_TMP_TEMPLATE",
            "/data/local/tmp/snow.XXXXXX",
        )
        with env.vars(self).apply():
            self.run(f'"{tmpdir_test}" --gdb', env="conanrun")
