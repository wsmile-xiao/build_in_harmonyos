from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class ShineTestConan(ConanFile):
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
        # L0d: explicit self.run() — execute the real consumer binary that
        # exercises the installed shine API.
        self.run("./test_shine", env="conanrun")
