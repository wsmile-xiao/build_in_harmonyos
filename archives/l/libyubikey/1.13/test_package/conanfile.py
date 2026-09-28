from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibyubikeyTestConan(ConanFile):
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
        # Runs the compiled consumer test (links libyubikey, uses yubikey.h).
        self.run("./libyubikey_test", env="conanrun")
        # Installed CLI smoke: the package ships modhex in bin/.
        self.run("modhex test | grep -q ifhgieif", env="conanrun")
