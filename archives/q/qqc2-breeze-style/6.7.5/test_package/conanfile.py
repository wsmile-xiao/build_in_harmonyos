#!/usr/bin/env python3
"""Conan test_package — qqc2-breeze-style 6.7.5.

Substantive consumer test (R34): builds a QCoreApplication + QQmlEngine
consumer that verifies the installed QML style payload (org.kde.breeze)
resolves through the QML import path — the same mechanism real consumers
use. No display server is required (QQmlEngine import path resolution and
file probing run headless).
"""
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Qqc2TestConan(ConanFile):
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

        prefixes = []
        libraries = []
        includes = []

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

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = paths_file
        tc.generate()

    def build(self):
        # OHOS: hnp cmake is an OHOS ELF that needs libc++_shared.so from
        # /system/lib64; without this prepend CMake.configure() dies with
        # "Error relocating cmake: _ZTINSt4__n1... symbol not found"
        # (exit 127) — gtksourceview5 5.22.0 precedent.
        os.environ["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        )
        cmake = CMake(self)
        with self._test_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        # R34/test discipline: run the consumer binary via self.run with a
        # bash -c wrapper exporting LD_LIBRARY_PATH at the shell level so
        # every dependency lib directory (including /system/lib64 for the
        # compatible libc++) is on the loader path.
        pkg = self.dependencies[self.tested_reference_str]
        exe = os.path.join(self.cpp.build.bindirs[0], "test_qqc2")
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dirs.append(os.path.join(dep.package_folder, "lib"))
        lib_dirs.append("/system/lib64")
        ld_path = os.pathsep.join(lib_dirs)
        # KDEInstallDirs layout: the QML module installs under lib/qml and
        # the kirigami platform plugin under lib/plugins (CMAKE_INSTALL_LIBDIR
        # = lib). Support the flat qml/plugins layout as fallback.
        pkg_root = pkg.package_folder
        qml_dir = os.path.join(pkg_root, "lib", "qml")
        if not os.path.isdir(qml_dir):
            qml_dir = os.path.join(pkg_root, "qml")
        plugins_dir = os.path.join(pkg_root, "lib", "plugins")
        if not os.path.isdir(plugins_dir):
            plugins_dir = os.path.join(pkg_root, "plugins")
        cmd = (
            "export LD_LIBRARY_PATH={ld} && "
            "export QT_QPA_PLATFORM=offscreen && "
            "export QML2_IMPORT_PATH={qml} && "
            "export QT_PLUGIN_PATH={plugins} && "
            "{exe} {pkg_root}"
        ).format(
            ld=shlex.quote(ld_path),
            qml=shlex.quote(qml_dir),
            plugins=shlex.quote(plugins_dir),
            exe=shlex.quote(exe),
            pkg_root=shlex.quote(pkg_root),
        )
        self.run(f'bash -c "{cmd}"', env="conanbuild")

    def _test_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env
