#!/usr/bin/env python3
"""test_package — runs the installed lha-ac tools on the target device."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class LhaAcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dependency = self.dependencies["lha-ac"]
        bindir = dependency.cpp_info.bindirs[0]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test() runs from the test package build folder, so address the
        # verification script through its recipe location and give it a
        # scratch directory to create archives in.
        script = os.path.join(self.recipe_folder, "test.sh")
        workdir = os.path.join(self.build_folder, "consumer")
        os.makedirs(workdir, exist_ok=True)
        self.run(
            f'"{bash}" "{script}" "{os.path.join(bindir, "lha")}"',
            cwd=workdir,
            env="conanrun",
        )
