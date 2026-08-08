#!/usr/bin/env python3
"""Conan test_package for libmpdclient 2.23."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class LibmpdclientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") if isinstance(compilers, dict) else None
        if not cc:
            raise RuntimeError("tools.build:compiler_executables must provide a C compiler")

        dependency = self.dependencies["libmpdclient"]
        include_dir = os.path.join(dependency.package_folder, "include")
        lib_dir = os.path.join(dependency.package_folder, "lib")
        source = os.path.join(self.source_folder, "test_libmpdclient.c")
        output = os.path.join(self.build_folder, "test_libmpdclient")
        self.run(
            f'"{cc}" "{source}" -I"{include_dir}" -L"{lib_dir}" '
            f'-lmpdclient -o "{output}"'
        )

    def test(self):
        if can_run(self):
            exe = os.path.join(self.build_folder, "test_libmpdclient")
            lib_dir = os.path.join(
                self.dependencies["libmpdclient"].package_folder, "lib"
            )
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'LD_LIBRARY_PATH="{lib_dir}" "{bash}" -c "{exe}"')
