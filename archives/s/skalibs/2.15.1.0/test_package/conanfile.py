from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class SkalibsTestConan(ConanFile):
    """test_package for skalibs — compiles a C program calling skalibs APIs."""
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
        # Run the test binary directly to substantively exercise skalibs APIs (R34).
        # L0d requires self.run() in test() — cmake.test() alone is not sufficient.
        self.run("./test_skalibs", env="conanrun")
