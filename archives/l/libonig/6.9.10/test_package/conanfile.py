#!/usr/bin/env python3
"""Consumer tests for the libonig C API and HarmonyOS runtime."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibonigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["OHOS_ARCH"] = (
                "arm64-v8a" if str(self.settings.arch) == "armv8" else "x86_64"
            )
        tc.generate()

        temp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(temp_dir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", temp_dir)
        env.vars(self, scope="run").save_script("libonig_test")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "libonig test_package must run on a native Linux/OHOS environment"
            )

        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_onig")
        self.run(test_binary, env=["conanrun", "libonig_test"])

        if str(self.settings.os) == "OHOS":
            ohos_binary = os.path.join(self.cpp.build.bindirs[0], "test_ohos")
            self.run(ohos_binary, env=["conanrun", "libonig_test"])
