#!/usr/bin/env python3
"""Consumer tests for the packaged wtype executable."""
import os
import glob

from conan import ConanFile


class WtypeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["wtype"].package_folder
        cache_folder = os.path.dirname(package_folder)
        build_folders = sorted(glob.glob(os.path.join(cache_folder, "b", "build-*")))
        build_folder = next(
            (folder for folder in build_folders if os.path.isfile(os.path.join(folder, "wtype"))),
            None,
        )
        if not build_folder:
            raise Exception("wtype build output was not found in the Conan build cache")

        test_script = os.path.join(self.source_folder, "test.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # HarmonyOS's sandbox allows execution from Conan's build folder but
        # denies execve() from the package folder and user temp directories.
        self.run(
            f'"{bash}" "{test_script}" "{package_folder}" "{build_folder}"',
            cwd=build_folder,
            env="conanrun",
        )
