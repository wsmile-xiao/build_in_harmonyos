from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AvroCppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # avro's public headers include <fmt/core.h>, <boost/...>, <zlib.h>;
        # declare them so CMakeDeps generates their config files.
        self.requires("boost/1.84.0", transitive_headers=True)
        self.requires("fmt/8.1.1", transitive_headers=True)
        self.requires("zlib/1.3.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
