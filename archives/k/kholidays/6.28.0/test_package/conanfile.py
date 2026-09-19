#!/usr/bin/env python3
"""Conan test_package for kholidays 6.28.0.

Verifies that the KF6Holidays library is discoverable via CMake
(find_package(KF6Holidays) + KF6::Holidays link) and that the public
astronomy API (SunRiseSet, SunEvents) computes astronomically sound
results (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KholidaysTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        qtdeclarative = self.dependencies.get("qtdeclarative")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if qtdeclarative:
            qml_pkg = qtdeclarative.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qml_pkg}/lib/cmake")'
            )
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qml_pkg}/lib")')
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
        if not can_run(self):
            self.output.info("Cross-built test_kholidays; runtime verification "
                             "is deferred to the OHOS target")
            return
        dep = self.dependencies[self.tested_reference_str]
        test_env = Environment()
        for d in self.dependencies.values():
            if d and d.package_folder:
                test_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(d.package_folder, "lib")
                )
        test_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder)
        )
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        with test_env.vars(self).apply():
            self.run(
                os.path.join(self.build_folder, "test_kholidays"),
                env="conanrun",
            )
