from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class PoundTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Directly run pound binary from the installed package
        self.run("pound -V 2>&1 | grep -q 'pound.*4.22'", env="conanrun")
