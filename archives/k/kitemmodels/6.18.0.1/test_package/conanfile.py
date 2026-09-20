#!/usr/bin/env python3
"""Conan test_package for kitemmodels 6.18.0.1.

R34: exercises the real KF6ItemModels C++ API (not a version() stub).
R53: proves the QML module org.kde.kitemmodels ships in the package, is
     importable through a fresh QQmlEngine pointed at the package import path,
     and that its QML types can be instantiated and behave correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KitemmodelsTestConan(ConanFile):
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

        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")'
                )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _qml_import_paths(self):
        paths = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for rel in ("lib/qml", "share/qml", "qml"):
                    candidate = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(candidate):
                        paths.append(candidate)
        return paths

    def test(self):
        lib_dirs = [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        plugin_dirs = [
            os.path.join(p.package_folder, "plugins")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        qml_paths = self._qml_import_paths()

        def joined(values, current=""):
            parts = [v for v in values if v]
            if current:
                parts.append(current)
            return os.pathsep.join(parts)

        env = Environment()
        env.define(
            "LD_LIBRARY_PATH",
            joined(lib_dirs, os.environ.get("LD_LIBRARY_PATH", "")),
        )
        env.define("QT_PLUGIN_PATH", joined(plugin_dirs))
        env.define("QML2_IMPORT_PATH", joined(qml_paths))
        env.define("QML_IMPORT_PATH", joined(qml_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("KITEMMODELS_QML_IMPORT_PATH", joined(qml_paths))

        self.output.info("test LD_LIBRARY_PATH=%s" % joined(lib_dirs))
        self.output.info("test QML_IMPORT_PATH=%s" % joined(qml_paths))

        binary = os.path.join(self.cpp.build.bindirs[0], "test_kitemmodels")
        with env.vars(self).apply():
            self.run('"%s"' % binary)
