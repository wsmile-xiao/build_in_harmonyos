#!/usr/bin/env python3
"""Conan test_package for kwidgetsaddons5 5.116.0.

The consumer links against KF5::WidgetsAddons (libKF5WidgetsAddons) and the
Qt5 Widgets libraries, exercising the real KPageWidgetModel API (R34: real
API usage, no fake test).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Kwidgetsaddons5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qt5 = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            # kwidgetsaddons5 uses cmake_find_mode=none: point the config-mode
            # search at the installed KF5WidgetsAddons cmake configs.
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s")'
                % os.path.join(pkg.package_folder, "lib", "cmake")
            )
        if qt5:
            qt_pkg = qt5.package_folder
            # The installed KF5WidgetsAddonsConfig.cmake does
            # find_dependency(Qt5Widgets 5.15.2), which resolves through the
            # qt5-qtbase per-module config dir.
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s")'
                % os.path.join(qt_pkg, "lib", "cmake")
            )
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s")' % os.path.join(qt_pkg, "lib"))
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s")' % os.path.join(qt_pkg, "include"))
        # The generators folder holds the CMakeDeps-generated aggregated
        # Qt5Config.cmake; it must come before the qt5-qtbase package dir.
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so shipped in the SDK's
        # llvm/lib directory; workers may not export it via LD_LIBRARY_PATH
        # (observed on OpenHarmonyPCDeveloper-CI-021). Prepend it so CMake's
        # TryCompile can link. Must not clobber conanbuild env on other hosts.
        env = Environment()
        for llvm_lib in sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
            )
        ):
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        # KPageWidgetModel exercises the widgets addon model API; run headless
        # in case a platform plugin is needed for resource init.
        env.define("QT_QPA_PLATFORM", "offscreen")
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(qt5.package_folder, "plugins", "platforms"),
            )
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kwidgetsaddons5"),
                env="conanrun",
            )
