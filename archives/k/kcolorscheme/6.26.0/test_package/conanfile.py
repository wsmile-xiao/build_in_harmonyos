#!/usr/bin/env python3
"""Conan consumer test for kcolorscheme 6.26.0."""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KcolorschemeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0")
        self.requires("kguiaddons/6.26.0")
        self.requires("ki18n/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        package = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qtbase = self.dependencies.get("qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if package:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{package.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')

        for dep_name in ("kconfig", "kguiaddons", "ki18n"):
            dependency = self.dependencies.get(dep_name)
            if dependency and dependency.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dependency.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dependency.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dependency.package_folder}/include")'
                )

        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as paths:
            paths.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            libdir = os.path.join(dependency.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if not (name.startswith("libKF6") and ".so" in name):
                    continue
                source = os.path.join(libdir, name)
                destination = os.path.join(compatibility_bin, name)
                if os.path.lexists(destination):
                    continue
                try:
                    os.symlink(source, destination)
                except OSError:
                    shutil.copy2(source, destination)

        runtime_env = Environment()
        for dependency in self.dependencies.values():
            if dependency.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dependency.package_folder, "plugins"),
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dependency.package_folder, "plugins", "platforms"),
                )
        if self.settings.os == "OHOS":
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        runtime_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        runtime_env.define("XDG_CACHE_HOME", os.path.join(self.build_folder, "xdg-cache"))
        runtime_env.define("XDG_CONFIG_HOME", os.path.join(self.build_folder, "xdg-config"))

        with runtime_env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kcolorscheme"),
                env="conanrun",
            )
