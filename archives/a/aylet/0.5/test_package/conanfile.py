#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/a/aylet/0.5/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class AyletTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "test_package requires tools.build:compiler_executables:c"
            )
        static_flag = " -static" if str(self.settings.os) == "OHOS" else ""
        source = os.path.join(self.source_folder, "test.c")
        output = os.path.join(self.build_folder, "test_aylet")
        self.run(
            f'"{cc}"{static_flag} "{source}" -o "{output}"',
            env="conanbuild",
        )

    def test(self):
        self.run(
            os.path.join(self.build_folder, "test_aylet"),
            env="conanrun",
        )
