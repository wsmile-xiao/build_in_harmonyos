#!/usr/bin/env python3
"""Consumer test for the anubis command-line application."""

import os
import shlex

from conan import ConanFile


class AnubisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c") or os.environ.get("CC") or "clang"
        self.run(
            "%s -std=c99 -O2 -Wall -Wextra test.c -o test_anubis"
            % shlex.quote(cc),
            env="conanbuild",
        )

    def test(self):
        package = self.dependencies["anubis"].package_folder
        candidates = (os.path.join(package, "bin", "anubis"),)
        binary = next((path for path in candidates if os.path.isfile(path)), None)
        if binary is None:
            raise RuntimeError("anubis executable is missing from the package")
        self.run(
            "./test_anubis %s" % shlex.quote(binary),
            env="conanrun",
        )
