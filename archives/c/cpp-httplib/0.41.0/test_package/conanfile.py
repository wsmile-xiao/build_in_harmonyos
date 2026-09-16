import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CppHttplibTestPackageConan(ConanFile):
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
            tc.cache_variables["CPP_HTTPLIB_BUILD_HARMONYOS_TEST"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(executable, env="conanrun")
            if str(self.settings.os) == "OHOS":
                harmonyos_executable = os.path.join(
                    self.cpp.build.bindir, "harmonyos_test"
                )
                self.run(harmonyos_executable, env="conanrun")
        else:
            self.output.info(
                "Cross-building: consumer execution is covered by the HDC device test"
            )
