import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GeogramTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        old_umask = os.umask(0) if self.settings.os == "OHOS" else None
        try:
            cmake.configure()
            cmake.build()
        finally:
            if old_umask is not None:
                os.umask(old_umask)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link consumer completed")
            return
        executable = os.path.join("bin", "geogram_probe")
        if self.settings.os == "Windows":
            executable += ".exe"
        self.run(executable, env="conanrun")
