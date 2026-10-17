#!/usr/bin/env python3
"""Conan test_package for karchive5 5.116.0 (KDE Frameworks 5 line).

Builds and runs a consumer that actually exercises the KF5Archive API:
it writes a ZIP archive through KZip, reopens it through the KArchive
polymorphic interface, walks the entry tree, and round-trips the payload.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KArchive5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # The karchive5 recipe uses cmake_find_mode=none so CMakeDeps does not
        # advertise its builddirs; point CMake at the package's own
        # KF5ArchiveConfig.cmake, and at qt5-qtbase (also cmake_find_mode=none
        # in its recipe) for the Qt5Core dependency it re-finds.
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qtbase = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            pkg_folder = os.fspath(pkg.package_folder).replace("\\", "/")
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{pkg_folder}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg_folder}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg_folder}/include")'
            )
        if qtbase:
            qt_pkg = os.fspath(qtbase.package_folder).replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # libKF5Archive.so has DT_NEEDED entries on the compression backends
        # (libzstd.so.1, libbz2, liblzma) shipped by the Conan packages, so all
        # dependency lib dirs must be on the loader path.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{0}" --output-on-failure'.format(
                    self.build_folder
                )
            )
