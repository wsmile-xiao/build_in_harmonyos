import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibmygpoTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        qt = self.dependencies["qt"].package_folder
        for module in ("Qt5", "Qt5Core", "Qt5Network"):
            tc.variables[module + "_DIR"] = os.path.join(qt, "lib", "cmake", module).replace("\\", "/")
        tc.variables["Mygpo-qt5_DIR"] = os.path.join(
            self.dependencies["libmygpo"].package_folder, "lib", "cmake", "mygpo-qt5").replace("\\", "/")
        tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run('"' + os.path.join(self.build_folder, "test_libmygpo") + '"', env="conanrun")
