import os
import shlex
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class SwhTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def layout(self):
        cmake_layout(self)
    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()
        VirtualRunEnv(self).generate()
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    def test(self):
        if can_run(self):
            plugins = os.path.join(self.dependencies["swh"].package_folder, "lib", "ladspa")
            self.run(shlex.quote(os.path.join(self.build_folder, "test_package")) + " " + shlex.quote(plugins), env="conanrun")
