#!/usr/bin/env python3
"""Conan test_package for kf5wayland 5.116.0 (KDE Frameworks 5 line).

Builds and runs a consumer that exercises the KF5Wayland API (R34): it
constructs real protocol objects from both libraries and calls the server
compositor factory. OHOS has no Wayland compositor, so no connection is
attempted - the constructors/factory run package code without socket I/O
(client protocol classes are passive until setup/binding; the server
Display only calls wl_display_create(), createListener is never reached).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Kf5WaylandTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # kf5wayland uses cmake_find_mode=none: its KF5WaylandConfig.cmake
        # re-finds the Qt6 modules (D-form build), so the qtbase/qtwayland
        # packages must be on the CMake search path.
        self.requires("qtbase/6.11.1.2")
        self.requires("qtwayland/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in (
            pkg,
            self.dependencies.get("qtbase"),
            self.dependencies.get("qtwayland"),
        ):
            if dep and dep.package_folder:
                base = os.fspath(dep.package_folder).replace("\\", "/")
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{base}/lib/cmake")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{base}/lib")')
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{base}/include")'
                )
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
        # libKF5WaylandClient/Server.so have DT_NEEDED entries on the Qt6
        # Wayland modules and libwayland-* shipped by the Conan packages,
        # so all dependency lib dirs must be on the loader path.
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
