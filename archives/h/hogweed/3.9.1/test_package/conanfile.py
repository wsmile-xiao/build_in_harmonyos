from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class HogweedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # nettle/bignum.h includes <gmp.h>; make gmp headers transitively available
        self.requires("gmp/6.3.0.1")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        self.run("./hogweed_test", env="conanrun")