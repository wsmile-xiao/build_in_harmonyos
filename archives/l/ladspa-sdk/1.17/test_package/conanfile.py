from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
import os


class LadspaSdkTestConan(ConanFile):
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
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Expose the package's example plugins so the consumer can dlopen()
        # the installed amp.so in addition to the consumer-built plugin.
        pkg = self.dependencies["ladspa-sdk"].package_folder
        os.environ.setdefault("CONAN_LADSPA_LIB",
                              os.path.join(pkg, "lib", "ladspa"))
        os.environ.setdefault("LADSPA_PATH",
                              os.path.join(pkg, "lib", "ladspa"))
        cmake = CMake(self)
        # The CMake target name is test_consumer; ctest runs it with the
        # consumer plugin path injected via add_test().
        self.run("ctest --output-on-failure", env="conanrun")
