#!/usr/bin/env python3
"""Conan test_package for libbitarray 2."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import mkdir
from conan.tools.layout import basic_layout


class LibbitarrayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._tool_command(compilers.get("c"), "clang")
        dep = self.dependencies["libbitarray"]
        include_dir = dep.cpp_info.includedirs[0]
        lib_dir = dep.cpp_info.libdirs[0]
        mkdir(self, self.build_folder)
        source = os.path.join(self.source_folder, "test.c")
        output = os.path.join(self.build_folder, "test_libbitarray")
        self.run(f'{cc} "{source}" -I"{include_dir}" -L"{lib_dir}" -lbitarr -o "{output}"')

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_libbitarray")
        self.run(test_bin, env="conanrun")

    def _tool_command(self, configured, fallback):
        tool = configured or shutil.which(fallback) or fallback
        if os.path.isfile(tool):
            try:
                with open(tool, "rb") as handle:
                    if handle.read(2) == b"#!":
                        return f"sh {tool}"
            except OSError:
                pass
        return tool
