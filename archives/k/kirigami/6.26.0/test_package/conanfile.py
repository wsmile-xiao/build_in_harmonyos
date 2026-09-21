#!/usr/bin/env python3
"""Conan test_package for Kirigami 6.26.0 on HarmonyOS PC.

Validates both dimensions of the package:
  * C++ consumer: links ``KF6::Kirigami`` and checks the exported meta objects.
  * QML consumer: asserts the installed QML module ``lib/qml/org/kde/kirigami``
    carries ``qmldir`` + the plugin shared object, then drives a real
    ``QQmlEngine`` that imports ``org.kde.kirigami`` and instantiates a type
    (R34/R40 — offscreen QPA, no display required).
"""
import glob
import os
import shutil
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KirigamiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtshadertools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        qt_extra = []
        for dep_name in ("qtdeclarative", "qtsvg", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        self._dump_test_dynamic_section()
        env = Environment()
        deps = list(self.dependencies.values()) + list(self.dependencies.test.values())
        kirigami = self.dependencies["kirigami"]
        qml_root = os.path.join(kirigami.package_folder, "lib", "qml")
        env.define("KIRIGAMI_PKG_DIR", kirigami.package_folder)
        env.define("KIRIGAMI_QML_DIR", qml_root)
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml"))
        env.prepend_path("QML2_IMPORT_PATH", qml_root)
        env.define("QT_QPA_PLATFORM", "offscreen")
        library_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in deps
            if dep and dep.package_folder
        ]
        runtime_prefix = "LD_LIBRARY_PATH={} QT_QPA_PLATFORM=offscreen".format(
            shlex.quote(os.pathsep.join(library_paths))
        )
        with env.vars(self).apply():
            self.run(
                '{} ctest --test-dir {} --output-on-failure --no-tests=error'.format(
                    runtime_prefix, shlex.quote(self.build_folder)
                ), env="",
            )
            self.run(
                '{} {}'.format(runtime_prefix, shlex.quote(os.path.join(self.cpp.build.bindirs[0], "test_kirigami"))), env="",
            )
            self.run(
                '{} {}'.format(
                    runtime_prefix,
                    shlex.quote(os.path.join(self.cpp.build.bindirs[0], "test_kirigami_harmonyos")),
                ), env="",
            )

    def _dump_test_dynamic_section(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_kirigami")
        self.output.info("OHOS test executable dynamic section:")
        self.run(
            "llvm-readelf -d {}".format(shlex.quote(executable)),
            ignore_errors=True,
        )

    def _prepare_runtime_links(self):
        runtime_dirs = {self.cpp.build.bindirs[0], self.build_folder}
        lib_sources = []
        deps = list(self.dependencies.values()) + list(self.dependencies.test.values())
        for dep in deps:
            if dep and dep.package_folder:
                # OHOS linker records some library siblings as ../bin/<name>.so.
                runtime_dirs.add(os.path.join(dep.package_folder, "bin"))
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        for src in lib_sources:
            for runtime_dir in runtime_dirs:
                os.makedirs(runtime_dir, exist_ok=True)
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)
