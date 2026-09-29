#!/usr/bin/env python3
"""Conan test package — rulex 3.8.6."""

import os
import shlex
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class RulexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["rulex"].package_folder
        executable = os.path.join(self.cpp.build.bindir, "test_rulex")
        database = os.path.join(self.cpp.build.bindir, "consumer.db")
        lexholder = os.path.join(package, "bin", "lexholder-ru")
        installed_database = os.path.join(
            package, "share", "freespeech", "rulex.db"
        )
        upstream_data = os.path.join(package, "res", "tests", "lexicon.test")

        self.run(
            f"{shlex.quote(executable)} {shlex.quote(database)}",
            env="conanrun",
        )
        self.run(
            " ".join(
                [
                    shlex.quote(sys.executable),
                    shlex.quote(os.path.join(self.source_folder, "test_rulex.py")),
                    shlex.quote(lexholder),
                    shlex.quote(database),
                    shlex.quote(installed_database),
                    shlex.quote(upstream_data),
                    shlex.quote(self.cpp.build.bindir),
                ]
            ),
            env="conanrun",
        )
