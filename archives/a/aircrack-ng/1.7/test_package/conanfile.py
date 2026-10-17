#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import can_run


class AircrackngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["aircrack-ng"]
        inc = dep.cpp_info.includedirs[0]
        cc = os.environ.get("CC", "cc")
        self.run(f'{cc} test.c -o test -I{inc}')

    def test(self):
        if can_run(self):
            self.run("./test", env="conanrun")
            dep = self.dependencies["aircrack-ng"]
            bin_path = os.path.join(dep.cpp_info.bindirs[0], "aircrack-ng")
            self.run(f'"{bin_path}" --help', env="conanrun")
