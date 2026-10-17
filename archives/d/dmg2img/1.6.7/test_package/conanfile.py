#!/usr/bin/env python3
"""Test package for dmg2img — verifies CLI binary functionality.

R34: test must actually use the tested package's binary.
Compiles test_dmg2img.c which calls dmg2img via popen() and verifies
the version string in the output.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Dmg2ImgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Get compiler from Conan conf (R33)
        comp_execs = self.conf.get("tools.build:compiler_executables", {})
        if isinstance(comp_execs, dict):
            cc = comp_execs.get("c", "clang")
        else:
            cc = "clang"
        src = os.path.join(self.source_folder, "test_dmg2img.c")
        self.run(f'{cc} -o test_dmg2img "{src}"')

    def test(self):
        # R34: Execute the tested binary to verify functionality
        self.run("./test_dmg2img", env="conanrun")
