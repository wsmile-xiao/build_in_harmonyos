#!/usr/bin/env python3
"""Conan test_package — slang 2.3.3

L1 test: verify the slang library can be linked and the slsh binary runs.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SlangTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        # Build and run the smoke test via CMake
        cmake = CMake(self)
        cmake.configure()
        if self.settings.os == "OHOS":
            cmake.build(cli_args=["--parallel", "1"])
        else:
            cmake.build()

        # If we can run (not cross-building), execute the test binary
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_slang")
            ret = self.run(f'"{bin_path}"', env="conanrun", ignore_errors=True)
            tp_passed = (ret == 0)
            print(f'HMBS_TEST_PACKAGE_RESULT={{"executed":true,"passed":{str(tp_passed).lower()},"command":"{bin_path}"}}')

            if not tp_passed:
                raise Exception("test_package: test_slang failed")

            # Also verify slsh binary is installed and can show version
            pkg_folder = self.dependencies["slang"].package_folder
            slsh_path = os.path.join(pkg_folder, "bin", "slsh")
            if os.path.exists(slsh_path):
                self.run(f'"{slsh_path}" --version', env="conanrun")
