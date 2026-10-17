#!/usr/bin/env python3
"""Conan test_package for kf5windowsystem 5.116.0 on HarmonyOS PC.

The consumer links KF5::WindowSystem (libKF5WindowSystem.so) plus Qt5 Gui
and exercises the real KWindowSystem / KWindowEffects API surface against
the always-compiled dummy backend that OHOS uses (X11 compiled out, no
Wayland platform plugin published). A second, __OHOS__-gated binary
asserts the HarmonyOS platform identity and the absence of a native
windowing system.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Kf5WindowSystemTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Regenerate a clean aggregated Qt5Config: qt5-qtbase only ships
        # per-module configs, and the consumer's
        # find_package(Qt5 COMPONENTS Core Gui Widgets) needs one
        # (ki18n5/5.116.0 pattern).
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qt5 = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{pkg.package_folder}/lib/cmake")'
            )
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg.package_folder}")')
        if qt5:
            qt_pkg = qt5.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        # The generators folder holds the CMakeDeps-generated Qt5 configs.
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
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
        qt5 = self.dependencies["qt5-qtbase"]
        # `env="conanrun"` supplies the aggregated LD_LIBRARY_PATH of every
        # dependency in the graph; the tested package's own lib dir is added
        # explicitly so the SONAME-linked libKF5WindowSystem.so resolves.
        libdirs = [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + [os.environ.get("LD_LIBRARY_PATH", "")]
        )
        # KWindowSystem constructs a QGuiApplication-dependent singleton:
        # run headless on the offscreen QPA (same adaptation as the
        # qt5-qtbase / adwaita-qt test packages).
        plugin_root = os.path.join(qt5.package_folder, "plugins")
        os.environ["QT_PLUGIN_PATH"] = plugin_root
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
            plugin_root, "platforms"
        )

        # OHOS-specific: the installed shared object must be an AArch64 ELF64
        # with its DT_SONAME, its SONAME link and the .codesign section, and
        # the header + CMake package config must be installed.
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(
            self.recipe_folder, "test_kf5windowsystem_artifacts.py"
        )
        bindir = self.cpp.build.bindirs[0]

        self.run(
            '"{}" "{}" "{}"'.format(sys.executable, script, package_folder),
            env="conanrun",
        )
        self.run(os.path.join(bindir, "test_kf5windowsystem"), env="conanrun")
        self.run(
            os.path.join(bindir, "test_kf5windowsystem_harmonyos"),
            env="conanrun",
        )
