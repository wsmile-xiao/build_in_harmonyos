import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MrboomTestConan(ConanFile):
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
        # libretro core is a dlopen()-style plugin: no CMakeDeps target to link,
        # drive it by absolute path like a frontend would.
        dep = self.dependencies["mrboom"]
        core = os.path.join(dep.package_folder, "lib", "mrboom_libretro.so")
        if not os.path.isfile(core):
            raise Exception(f"mrboom core not found in package: {core}")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_mrboom")
        self.run(f'"{test_bin}" "{core}"')
