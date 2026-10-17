"""Conan test_package for fastjar 0.98.

Tests that the fastjar binary is installed and functional by:
1. Running `fastjar --version` to verify it executes
2. Creating a test JAR file and listing its contents
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class FastjarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # fastjar binary should be in PATH via VirtualRunEnv
            self.run("fastjar --version", env="conanrun")

            # Create a test file, add to JAR, then list
            test_file = os.path.join(self.build_folder, "hello.txt")
            with open(test_file, "w") as f:
                f.write("hello world\n")
            jar_file = os.path.join(self.build_folder, "test.jar")
            self.run(f'fastjar cf "{jar_file}" "{test_file}"', env="conanrun")
            self.run(f'fastjar tf "{jar_file}"', env="conanrun")
