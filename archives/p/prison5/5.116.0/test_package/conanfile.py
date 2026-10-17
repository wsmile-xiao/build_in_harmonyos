#!/usr/bin/env python3
"""Conan test_package for prison5 5.116.0 (L1 official test).

Consumer-side verification (R34): the C++ test links KF5::Prison and
drives the real public API - the Prison::createBarcode factory for every
barcode type of this package's configuration (QRCode / Code39 / Code93 /
Code128 / Aztec built in; Null / DataMatrix / PDF417 / EAN13 null-pointer
contract), setData/data and setData(QByteArray)/byteArrayData round-trips
and toImage rendering that exercises the QPainter path and the qrencode
backend - plus HarmonyOS-specific checks (R53): the loaded libKF5Prison.so
carries the unversioned DT_SONAME and a DT_RUNPATH (E537 install-RPATH
adaptation).

test() really executes the built binary through self.run() (L0d / R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Prison5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        # Consume the native Qt5 configs shipped inside qt5-qtbase (same
        # wiring as the library build).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        if str(self.settings.os) == "OHOS":
            # Same Linux-like platform force as the library build so the
            # native Qt5 configs apply their POSIX settings.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qtbase = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                % pkg.package_folder
            )
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % pkg.package_folder)
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % qt_pkg)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _build_env(self):
        # The Qt host tools (moc/rcc) need the compatible libc++ first.
        env = Environment()
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define(
            "XDG_DATA_HOME", os.path.join(self.build_folder, "xdg-data")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_prison5"),
                env="conanrun",
            )
