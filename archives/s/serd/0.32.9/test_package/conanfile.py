import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SerdTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()

        package_folder = self.dependencies["serd"].package_folder
        serdi = os.path.join(package_folder, "bin", "serdi")
        sample = os.path.join(self.source_folder, "sample.ttl")
        output = os.path.join(self.build_folder, "sample.nt")
        self.run(f'"{serdi}" -i turtle -o ntriples "{sample}" > "{output}"')
        with open(output, "r", encoding="utf-8") as handle:
            data = handle.read()
        if "<http://example.org/s>" not in data or '"hello"' not in data:
            raise RuntimeError("serdi did not convert sample Turtle input as expected")
