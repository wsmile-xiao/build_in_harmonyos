import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibnclTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test.cpp", "fixtures/*"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Match the package build's OHOS serial mode (no make jobserver FIFO).
        build_args = ["-j1"] if str(self.settings.os) == "OHOS" else None
        cmake.build(build_tool_args=build_args)

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "Native execution is required for libncl consumer assertions")
        executable = os.path.join(self.build_folder, self.cpp.build.bindirs[0],
                                  "test_ncl")
        fixtures = os.path.join(self.source_folder, "fixtures")
        args = [executable,
                os.path.join(fixtures, "characters.nex"),
                os.path.join(fixtures, "somebrlens.nex")]
        self.run(" ".join(shlex.quote(arg) for arg in args), env="conanrun")
