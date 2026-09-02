#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class MunitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return executables.get("c", "clang")

    def build(self):
        dependency = self.dependencies["munit"]
        include_dirs = [
            os.path.join(dependency.package_folder, directory)
            for directory in (dependency.cpp_info.includedirs or ["include"])
        ]
        library_dirs = [
            os.path.join(dependency.package_folder, directory)
            for directory in (dependency.cpp_info.libdirs or ["lib"])
        ]
        libraries = list(dependency.cpp_info.libs or ["munit"])
        binary = os.path.join(self.build_folder, "test_munit")
        command = [self._compiler(), "-std=c99", "-O2"]
        command.extend("-I" + directory for directory in include_dirs)
        command.append(os.path.join(self.source_folder, "test_munit.c"))
        command.extend("-L" + directory for directory in library_dirs)
        command.extend("-l" + library for library in libraries)
        command.extend(["-o", binary])
        self.run(shlex.join(command), cwd=self.build_folder, env="conanbuild")

    def test(self):
        binary = os.path.join(self.build_folder, "test_munit")
        tmpdir = os.path.join(self.build_folder, "munit-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.run(
            f"MUNIT_TMPDIR={shlex.quote(tmpdir)} {shlex.quote(binary)}",
            env="conanrun",
        )
