#!/usr/bin/env python3
"""Consumer tests for the libplist C API and HarmonyOS integration."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibplistTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        temp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(temp_dir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", temp_dir)
        env.vars(self, scope="run").save_script("libplist_test")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "libplist test_package must run on a native Linux/OHOS environment"
            )

        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_libplist")
        self.run(test_binary, env=["conanrun", "libplist_test"])

        if str(self.settings.os) == "OHOS":
            ohos_binary = os.path.join(self.cpp.build.bindirs[0], "test_ohos")
            self.run(ohos_binary, env=["conanrun", "libplist_test"])
