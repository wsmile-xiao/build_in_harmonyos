#!/usr/bin/env python3
"""Conan test_package for kdbusaddons5 (KF5/Qt5) 5.116.0."""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Kdbusaddons5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt5DBus is needed to link the KF5::DBusAddons target and is only
        # provided by the qt5-qtbase DBus variant.
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        if str(self.settings.os) in ("Linux", "OHOS"):
            if str(self.settings.os) == "OHOS":
                compilers = self.conf.get(
                    "tools.build:compiler_executables", default={}, check_type=dict
                ) or {}
                compiler = compilers.get("c") or compilers.get("cpp")
                if compiler:
                    native_dir = os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(compiler)))
                    )
                    sysroot = os.path.join(native_dir, "sysroot")
                    if os.path.isdir(sysroot):
                        tc.variables["CMAKE_SYSROOT"] = self._cmake_path(sysroot)
                targets = {
                    "armv8": "aarch64-linux-ohos",
                    "x86_64": "x86_64-linux-ohos",
                }
                target = targets.get(str(self.settings.arch))
                if target:
                    tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                    tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target
        tc.generate()

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{self._cmake_path(pkg.package_folder)}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = self._cmake_path(qtbase.package_folder)
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _cmake_path(path):
        return os.fspath(path).replace("\\", "/")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        source = os.path.join(qt_package_folder, "mkspecs", "linux-clang")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs", "linux-clang"
        )
        if os.path.isdir(source) and not os.path.exists(expected):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self) and not cross_building(self):
            tp_bin = os.path.join(self.build_folder, "..", "..", "bin")
            os.makedirs(tp_bin, exist_ok=True)
            for dep in self.dependencies.values():
                libdir = (
                    os.path.join(dep.package_folder, "lib")
                    if dep.package_folder
                    else None
                )
                if libdir and os.path.isdir(libdir):
                    for name in os.listdir(libdir):
                        if name.startswith("libKF5") and name.endswith(".so"):
                            link = os.path.join(tp_bin, name)
                            if not os.path.lexists(link):
                                try:
                                    os.symlink(os.path.join(libdir, name), link)
                                except OSError:
                                    shutil.copy2(os.path.join(libdir, name), link)

        env = Environment()
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        with env.vars(self).apply():
            if cross_building(self):
                self.output.info(
                    "Skipping test_package execution during cross-compilation; "
                    "target execution is required on OHOS"
                )
                return
            if can_run(self):
                cmake = CMake(self)
                cmake.test()
                self.run(
                    os.path.join(self.cpp.build.bindirs[0], "test_kdbusaddons5"),
                    env="conanrun",
                )
