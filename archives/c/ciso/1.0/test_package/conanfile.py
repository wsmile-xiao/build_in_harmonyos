from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CisoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Directly execute the ciso binary via conanrun env (PATH includes bin/)
        self.run("ciso", env="conanrun")

        # Run the CMake test program (also executes ciso via popen)
        cmake = CMake(self)
        cmake.test()
