import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LpSolveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link consumer test completed")
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_lp_solve")
        self.run(executable, env="conanrun")
        self.run(f"{executable} --fault-missing-model", env="conanrun")
        dependency = self.dependencies["lp_solve"]
        command = os.path.join(dependency.cpp_info.bindirs[0], "lp_solve")
        self.run(f"{command} -h", env="conanrun")
