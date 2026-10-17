#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile


class LibtommathTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies[self.tested_reference_str]
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c", "clang")
        include_dir = dep.cpp_info.includedirs[0]
        lib_dir = dep.cpp_info.libdirs[0]
        self.run(
            " ".join(
                [
                    shlex.quote(cc),
                    "-std=c11",
                    f"-I{shlex.quote(include_dir)}",
                    "test.c",
                    f"-L{shlex.quote(lib_dir)}",
                    "-ltommath",
                    f"-o{shlex.quote(os.path.join(self.build_folder, 'test_libtommath'))}",
                ]
            ),
            cwd=self.build_folder,
        )

    def test(self):
        self.run(os.path.join(self.build_folder, "test_libtommath"))
