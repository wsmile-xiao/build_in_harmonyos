#!/usr/bin/env python3
"""Consumer test for the packaged i2pd command-line executable."""

import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import save


class I2pdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def test(self):
        package_folder = self.dependencies["i2pd"].package_folder
        executable = os.path.join(package_folder, "bin", "i2pd")
        self.run(f'"{executable}" --version', env="conanrun")
        self.run(f'"{executable}" --help', env="conanrun")

        invalid_config = os.path.join(self.build_folder, "invalid-i2pd.conf")
        save(self, invalid_config, "this.option.does.not.exist = true\n")
        runenv = VirtualRunEnv(self).vars()
        with runenv.apply():
            result = subprocess.run(
                [executable, "--conf", invalid_config],
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        self.output.info(result.stdout)
        if result.returncode == 0 or "unrecognised option" not in result.stdout.lower():
            raise AssertionError(
                "i2pd did not reject the deliberately invalid configuration option"
            )
