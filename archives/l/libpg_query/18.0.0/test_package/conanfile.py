from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.gnu import PkgConfigDeps
from conan.tools.cmake import CMake, CMakeToolchain
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.build_folder, "test_libpg_query")
            self.run(bin_path, env="conanrun")
