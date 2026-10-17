from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tested = self.dependencies[self.tested_reference_str]
        tc.preprocessor_definitions["UCOMMON_WITH_SSL"] = (
            str(tested.options.with_ssl) != "False"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindir, "test_package")
        self.run(cmd, env="conanrun")
