#!/usr/bin/env python3
"""Conan test_package for libkexiv2 26.04.0.

Verifies that the installed KExiv2Qt6 CMake package is consumable and that the
public KExiv2 API performs real metadata work: the test writes a JPEG fixture
with Qt, then runs EXIF, date/time and XMP write/read round trips against it
(R34). See test_package.cpp for the 24 checks.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Libkexiv2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    # Soname aliases of the shared libraries loaded at runtime. The OHOS loader
    # rejects libraries reached through a symlink (E018/E511), so the
    # libQt6Core.so.6 -> libQt6Core.so.6.11.1 chains shipped by the conan
    # packages have to be materialised as regular-file copies.
    _runtime_sonames = ("libQt6Core.so.6", "libQt6Gui.so.6", "libexpat.so.1")

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # libkexiv2 and qtbase are both consumed through cmake_find_mode=none,
        # so declare their config directories explicitly (libkcddb 26.04.3
        # test_package precedent).
        lines = []
        for dep in self.dependencies.host.values():
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w"
        ) as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _runtime_environment(self):
        runtime_dir = os.path.join(self.build_folder, "runtime-libs")
        os.makedirs(runtime_dir, exist_ok=True)
        search_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        ]
        env = Environment()
        for soname in self._runtime_sonames:
            destination = os.path.join(runtime_dir, soname)
            if not os.path.exists(destination):
                for directory in search_dirs:
                    candidate = os.path.join(directory, soname)
                    if os.path.isfile(candidate):
                        shutil.copy2(os.path.realpath(candidate), destination)
                        self.output.info(f"materialised shared library alias {soname}")
                        break
        env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(qtbase.package_folder, "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def test(self):
        if not can_run(self):
            return
        # bin dirs are relative to the build folder ("." in the single-config
        # cmake_layout), so resolve the executable to an absolute path before
        # switching the working directory.
        executable = os.path.join(
            self.build_folder, self.cpp.build.bindirs[0], "test_package"
        )
        work_dir = os.path.join(self.build_folder, "test-run")
        os.makedirs(work_dir, exist_ok=True)
        with self._runtime_environment().vars(self).apply():
            self.run(f'"{executable}" "{work_dir}"', cwd=work_dir)
