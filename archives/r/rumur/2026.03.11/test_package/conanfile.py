#!/usr/bin/env python3
"""
Test package for rumur — verifies the rumur model checker binary works
and includes an OHOS-specific consumer case.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment


class RumurTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        pkg_folder = self.dependencies["rumur"].package_folder
        rumur_bin = os.path.join(pkg_folder, "bin", "rumur")
        assert os.path.isfile(rumur_bin), f"rumur binary not found at {rumur_bin}"

        # Set LD_LIBRARY_PATH so rumur can find libgmp/libgmpxx
        lib_dir = os.path.join(pkg_folder, "lib")
        env = Environment()
        if os.path.isdir(lib_dir):
            env.define("LD_LIBRARY_PATH", lib_dir)

        # R34: exercise the packaged artifact with the real smoke-test script
        # (same shape as the other CLI recipes in this archive: abcde/aamath).
        # Absolute paths are derived from recipe_folder so the test does not
        # depend on the build folder layout. The script runs:
        #   1. the package binary is present and executable
        #   2. `rumur --version` executes and links
        #   3. `rumur --output=/dev/null model.m` (ordinary consumer case)
        #   4. `rumur --output=/dev/stdout model.m` (OHOS-specific case: the
        #      patched code path, matching upstream rumur-run's invocation)
        script = os.path.join(self.recipe_folder, "test_rumur.sh")
        model = os.path.join(self.recipe_folder, "model.m")

        with env.vars(self).apply():
            self.run(f'sh "{script}" "{rumur_bin}" "{model}"')
