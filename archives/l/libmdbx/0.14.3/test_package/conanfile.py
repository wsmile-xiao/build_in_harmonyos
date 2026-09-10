import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibmdbxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer binaries were built and linked; runtime execution skipped")
            return
        executables = ["test_libmdbx_c", "test_libmdbx_cpp"]
        if str(self.settings.os) == "OHOS":
            executables.append("test_libmdbx_ohos")
        for executable in executables:
            self.run(os.path.join(self.cpp.build.bindirs[0], executable), env="conanrun")
