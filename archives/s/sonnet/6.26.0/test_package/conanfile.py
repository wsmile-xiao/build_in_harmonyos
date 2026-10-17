import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SonnetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The tested package (sonnet) ships its own KF6SonnetConfig.cmake
        # (cmake_find_mode=none, so CMakeDeps generates no find module for
        # it), and that config calls find_dependency(Qt6Core). Therefore both
        # the sonnet and qtbase cmake dirs must be on CMAKE_PREFIX_PATH.
        tc = CMakeToolchain(self)
        lines = []
        sonnet = self.dependencies.get("sonnet")
        if sonnet:
            sn_pkg = sonnet.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{sn_pkg}/lib/cmake")')
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
        if lines:
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Also run the binary directly
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_sonnet")
        self.run(bin_path, env="conanrun")