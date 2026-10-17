from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class IntelHdcpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

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
        # Run the consumer test binary that exercises the installed
        # libhdcpsdk API (parameter-validation paths, deterministic without a
        # running hdcpd daemon).
        self.run("./example", env="conanrun")