import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OrbuculumTestConan(ConanFile):
    """test_package for orbuculum — exercises the packaged liborb C API and the
    installed command line tools."""

    settings = "os", "arch", "compiler", "build_type"
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
        # 1) link against the packaged liborb and drive the COBS API
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "orbuculum_cobs_test"),
            env="conanrun",
        )
        # 2) run the installed command line tools (test.sh is POSIX sh)
        shell = self._shell()
        self.run(f'"{shell}" "{os.path.join(self.recipe_folder, "test.sh")}"', env="conanrun")

    def _shell(self):
        for candidate in (os.environ.get("CONFIG_SHELL"), shutil.which("bash"),
                          shutil.which("sh"), "/bin/sh"):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/bin/sh"
