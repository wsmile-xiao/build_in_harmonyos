import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MPUnitsTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            if str(self.settings.os) == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
                tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # mp-units is a C++20 library. The shared OHOS profile defaults to
        # C++17 for general packages, so make the consumer requirement
        # explicit instead of relying on target_compile_features to override
        # Conan's profile flags.
        tc.cache_variables["CMAKE_CXX_STANDARD"] = 20
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
