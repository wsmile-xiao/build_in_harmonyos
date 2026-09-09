#!/usr/bin/env python3
"""Conan test package — libsodium 1.0.20."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibsodiumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define c"
            )
        compiler_command = shlex.split(cc)

        dependency = self.dependencies["libsodium"]
        include_dir = dependency.cpp_info.includedirs[0]
        library_dir = dependency.cpp_info.libdirs[0]
        source = os.path.join(self.source_folder, "test_sodium.c")
        executable = os.path.join(self.build_folder, "test_sodium")

        self.run(
            " ".join(
                [
                    *(shlex.quote(argument) for argument in compiler_command),
                    "-std=c99",
                    f"-I{shlex.quote(include_dir)}",
                    shlex.quote(source),
                    f"-L{shlex.quote(library_dir)}",
                    "-lsodium",
                    "-o",
                    shlex.quote(executable),
                ]
            ),
            env="conanbuild",
        )

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_sodium"), env="conanrun")
        else:
            self.output.info(
                "Cross build: run test_sodium on the HarmonyOS target"
            )
