#!/usr/bin/env python3
"""Conan test_package for lolcode — terminal tool (binary) test.

L1 test: verify the lolcode interpreter binary works.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LolcodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Get the lolcode binary path from the dependency
            lolcode = self.dependencies["lolcode"].cpp_info.bindirs[0]
            lolcode_bin = os.path.join(lolcode, "lolcode")
            # Create a simple LOLCODE test program
            test_file = os.path.join(self.build_folder, "test.lol")
            with open(test_file, "w") as f:
                f.write('HAI 1.2\nVISIBLE "HAI WORLD!"\nKTHXBYE\n')
            # Run the interpreter
            self.run(f'"{lolcode_bin}" -f "{test_file}"', env="conanrun")
