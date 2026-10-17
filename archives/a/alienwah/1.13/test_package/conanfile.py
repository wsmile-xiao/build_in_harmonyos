#!/usr/bin/env python3
"""Conan test_package for AlienWah 1.13."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AlienwahTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value).replace("\\", "/"))

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("cpp", "clang++")

    def test(self):
        plugin = os.path.join(
            self.dependencies["alienwah"].package_folder, "lib", "ladspa", "aw.so"
        )
        if not os.path.isfile(plugin):
            raise ConanException(f"missing packaged plugin: {plugin}")

        include_flags = [
            f"-I{path}" for path in self.dependencies["alienwah"].cpp_info.includedirs
        ]
        source = os.path.join(self.source_folder, "test_descriptor.cpp")
        exe = os.path.join(self.build_folder, "test_descriptor")
        self.run(
            f"{self._quote(self._compiler())} "
            f"{' '.join(self._quote(flag) for flag in include_flags)} "
            f"{self._quote(source)} -ldl -o {self._quote(exe)}",
            env="conanbuild",
        )
        if can_run(self):
            self.run(f"{self._quote(exe)} {self._quote(plugin)}", env="conanrun")
        else:
            self.output.warning("Skipping descriptor runtime test because target binaries cannot run")
