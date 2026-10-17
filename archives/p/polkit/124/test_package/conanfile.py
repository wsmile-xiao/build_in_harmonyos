import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PolkitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test source also uses glib-2.0 (g_print/g_free)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_polkit" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
