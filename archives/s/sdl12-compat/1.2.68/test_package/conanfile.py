import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class Sdl12CompatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
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
        if can_run(self):
            environment = Environment()
            package_folder = self.dependencies["sdl12-compat"].package_folder
            environment.define(
                "EXPECTED_SDL2_PATH",
                os.path.join(package_folder, "lib", "libSDL2-2.0.so.0"),
            )
            environment.define("SDL_VIDEODRIVER", "dummy")
            environment.define("SDL_AUDIODRIVER", "dummy")
            with environment.vars(self).apply():
                executable = os.path.join(self.cpp.build.bindirs[0], "test_sdl12_compat")
                self.run(executable, env="conanrun")
