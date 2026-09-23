#!/usr/bin/env python3
"""Conan test_package — phonon 4.12.0 L1 test.

Validates that the packaged libphonon4qt6.so actually works: links a
consumer C++ program against Phonon::phonon4qt6 and calls the Phonon API
(Phonon::phononVersion(), Phonon::BackendCapabilities::availableMimeTypes()).

qtbase/qttools/qt5compat use cmake_find_mode=none, so CMakeDeps does not
generate their config files; manually inject their lib/cmake dirs into
CMAKE_PREFIX_PATH via conan_cmakedeps_paths.cmake (karchive precedent).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PhononTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qt5compat/6.11.1")
        self.requires("qttools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        dep_names = ("qtbase", "qt5compat", "qttools")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        targets = [pkg] if pkg else []
        targets += [
            self.dependencies.get(n) for n in dep_names if self.dependencies.get(n)
        ]
        for dep in targets:
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(
            'ctest --test-dir "{}" --output-on-failure'.format(self.build_folder),
            env="conanrun",
        )