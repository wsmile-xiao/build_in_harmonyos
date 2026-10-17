#!/usr/bin/env python3
"""Conan test_package for kplotting5 5.116.0 (L1 official test).

Consumer-side verification (R34): the C++ test links KF5::Plotting and drives
the real public API — KPlotWidget, KPlotObject, KPlotPoint, KPlotAxis —
asserting observable behaviour (point storage/lookup, axis tick maths, plot
object pen/brush/size state, widget plot-object management and colors), not
just that the library links.

HarmonyOS-specific assertions (R53): test.cpp additionally asserts that
  * QApplication runs on the HarmonyOS "offscreen" QPA platform plugin (the
    headless GUI path a Widgets library uses on OHOS);
  * the loaded libKF5Plotting.so carries the OHOS-required unversioned
    DT_SONAME and a DT_RUNPATH (E537: the installed ELF is linked with its
    final install RPATH and is never rewritten post-link, so OHOS keeps
    mmap'ing it PROT_EXEC);
  * the packaged libKF5Plotting.so carries a .codesign section (the recipe
    signs it with the OHOS binary-sign-tool).

test() really executes the built binary through self.run() (L0d / R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KPlotting5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        # The tested kplotting5 package installs its own native
        # KF5PlottingConfig.cmake (find_dependency(Qt5Widgets) + exported
        # KF5::Plotting target); suppress the CMakeDeps forwarding config so
        # it does not shadow the native one (recipe-side precedent).
        deps.set_property("kplotting5", "cmake_find_mode", "none")
        # qt5-qtbase provides its native Qt5 configs; generate the aggregated
        # one only for the components test_package needs.
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qt5 = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            # Native KF5PlottingConfig.cmake + KF5PlottingTargets.cmake.
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(pkg.package_folder)
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH '
                '"{}/lib/cmake/KF5Plotting")'.format(pkg.package_folder)
            )
        if qt5:
            qt_pkg = qt5.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
        # The generators folder holds the CMakeDeps-generated Qt5 configs.
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        # Chain-wide convention (kcalcore5/kpeople5): force the Linux
        # platform in test_package too — the OHOS conan toolchain maps
        # os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS and the CMake >= 4 workers
        # ship no Platform/ module for it.
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if str(self.settings.arch) == "armv8":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        elif str(self.settings.arch) == "x86_64":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "x86_64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _build_env(self):
        # The Qt host tools (moc for the Q_OBJECT-free test — still needed by
        # AUTOMOC scanning — and any qmake query) load the compatible libc++
        # first.
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("XDG_DATA_HOME",
                   os.path.join(self.build_folder, "xdg-data"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kplotting5"),
                env="conanrun",
            )
