#!/usr/bin/env python3
"""Conan recipe for kglobalaccel 6.18.0 (KDE Frameworks 6) on HarmonyOS PC.

Global desktop shortcuts library (Qt6::DBus/Gui/Widgets based).

HarmonyOS adaptations:
  - WITH_X11=OFF            : no X11 backend on OHOS (Qt6::GuiPrivate X11 paths
                              are only used when WITH_X11=ON).
  - KF_IGNORE_PLATFORM_CHECK=TRUE : allow building on non-mainstream platforms.
  - qttools as build_requires      : provides Qt6LinguistTools (lrelease) used
                              by ecm_install_po_files_as_qm.
  - Qt6::DBus comes from qtbase-sql-dbus (DBus-enabled qtbase build).
  - Qt6Qml comes from qtdeclarative (build_requires, only needed for the
    upstream tests target; upstream registers no ctest tests for it —
    kglobalacceltest is executed separately on device, see notes.md
    "上游测试真实执行" / manifest test_results.upstream 1/1).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KGlobalAccelConan(ConanFile):
    name = "kglobalaccel"
    version = "6.18.0"
    description = "KDE Frameworks 6 - Global desktop shortcuts library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kglobalaccel"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::DBus + Gui + Widgets (qtbase-sql-dbus carries the DBus module)
        self.requires("qtbase-sql-dbus/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")
        self.build_requires("qttools/6.11.1")
        # Only needed to compile tests/kglobalacceltest (Qt6Qml). The test is
        # not registered with ctest upstream, see notes.md / reports.
        self.build_requires("qtdeclarative/6.11.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["WITH_X11"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        qt_prefixes = []
        qtd = self.dependencies.get("qtbase-sql-dbus")
        if qtd and qtd.package_folder:
            qt_prefixes.append(qtd.package_folder)
        qtt = self.dependencies.build.get("qttools")
        if qtt and qtt.package_folder:
            qt_prefixes.append(qtt.package_folder)
        qml = self.dependencies.build.get("qtdeclarative")
        if qml and qml.package_folder:
            qt_prefixes.append(qml.package_folder)
        if qt_prefixes:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_prefixes)
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        # qtbase-sql-dbus must be found first so Qt6Config resolves to it
        # (qtdeclarative pulls a plain qtbase/6.11.1 as its own requirement).
        host_deps = [self.dependencies.get("qtbase-sql-dbus")]
        build_deps = [
            self.dependencies.build.get("qttools"),
            self.dependencies.build.get("qtdeclarative"),
        ]
        for dep in host_deps + build_deps:
            if dep and dep.package_folder:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            for rel in ("modules", "find-modules", "kde-modules"):
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{os.path.join(ecm.package_folder, "share", "ECM", rel)}")')
        lines.append(f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream registers no ctest tests (tests/CMakeLists.txt uses plain
        # add_executable, no ecm_add_test/add_test). Running ctest is therefore
        # a no-op that exits 0 (no --no-tests=error so an empty suite passes).
        self.run("ctest --test-dir \"{}\" --output-on-failure".format(self.build_folder))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6GlobalAccel", "KF6GlobalAccelPrivate"]
