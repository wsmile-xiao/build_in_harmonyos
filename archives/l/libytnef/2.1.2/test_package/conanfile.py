import base64
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibytnefTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: test_package execution is skipped")
            return
        # The sample message ships base64-encoded: a binary blob in the PR diff
        # cannot be applied by the CI ``git apply`` checkout.
        encoded = os.path.join(self.recipe_folder, "one-file.tnef.b64")
        sample = os.path.join(self.build_folder, "one-file.tnef")
        with open(encoded, "rb") as src, open(sample, "wb") as dst:
            dst.write(base64.b64decode(src.read()))
        executable = os.path.join(self.cpp.build.bindir, "test_package")
        self.run(f'"{executable}" "{sample}"', env="conanrun")
