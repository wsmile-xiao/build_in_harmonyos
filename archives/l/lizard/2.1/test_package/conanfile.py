#!/usr/bin/env python3
"""Conan test_package for lizard 2.1."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class LizardTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["lizard"]
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler.get("c") or os.environ.get("CC") or "clang"
        include_dir = dep.cpp_info.includedirs[0]
        lib_dir = dep.cpp_info.libdirs[0]
        source = os.path.join(self.source_folder, "test.c")
        output = os.path.join(self.build_folder, "test_lizard")
        command = (
            f"{shlex.quote(cc)} {shlex.quote(source)} "
            f"-I{shlex.quote(include_dir)} -L{shlex.quote(lib_dir)} "
            f"-llizard -o {shlex.quote(output)}"
        )
        self.run(command)

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_lizard"), env="conanrun")
