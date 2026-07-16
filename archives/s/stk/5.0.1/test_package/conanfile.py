#!/usr/bin/env python3
"""Conan test_package for stk 5.0.1."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class StkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("cpp", "clang++")

    def build(self):
        dep = self.dependencies["stk"]
        include_flags = " ".join(f'-I"{d}"' for d in dep.cpp_info.includedirs)
        lib_path = os.path.join(dep.package_folder, "lib", "libstk.a")
        src = os.path.join(self.source_folder, "test_stk.cpp")
        out = os.path.join(self.build_folder, "test_stk")

        ld_flags = "-lm"
        if str(self.settings.os) == "OHOS":
            ld_flags = f"{ld_flags} -fuse-ld=/data/service/hnp/bin/ld"

        self.run(
            f'"{self._compiler()}" -std=c++11 {include_flags} '
            f'"{src}" "{lib_path}" {ld_flags} -o "{out}"'
        )

    def test(self):
        exe = os.path.join(self.build_folder, "test_stk")
        if str(self.settings.os) == "OHOS":
            os.chmod(exe, 0o755)
        self.run(f'"{exe}"', env="conanrun")
