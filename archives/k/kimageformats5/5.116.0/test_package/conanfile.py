#!/usr/bin/env python3
"""Conan test_package for kimageformats5 5.116.0 (KDE Frameworks 5 line)."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KImageFormats5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        qtbase = self.dependencies.get("qt5-qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if pkg:
            # The CMake test checks the plugin folder of the tested package.
            tc.variables["KIMAGEFORMATS5_ROOT"] = os.fspath(pkg.package_folder)
        tc.generate()

        # qt5-qtbase uses cmake_find_mode=none; point CMake at its configs.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if qtbase:
            qt_pkg = os.fspath(qtbase.package_folder).replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
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
        if can_run(self):
            env = Environment()
            qtbase = self.dependencies.get("qt5-qtbase")
            if qtbase:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib")
                )
            pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
            if pkg:
                for dep_name in ("openexr", "libraw"):
                    dep = pkg.dependencies.get(dep_name)
                    if dep:
                        env.prepend_path(
                            "LD_LIBRARY_PATH",
                            os.path.join(dep.package_folder, "lib"),
                        )
            if os.path.isdir("/system/lib64"):
                env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            env.define("QT_QPA_PLATFORM", "offscreen")
            with env.vars(self).apply():
                self.run(
                    'ctest --test-dir "{0}" --output-on-failure'.format(
                        self.build_folder
                    )
                )
