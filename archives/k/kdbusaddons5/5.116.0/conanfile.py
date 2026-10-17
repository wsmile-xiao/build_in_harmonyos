#!/usr/bin/env python3
"""Conan recipe for kdbusaddons5 5.116.0 (KF5/Qt5) on HarmonyOS PC.

kdbusaddons5 is the KDE Frameworks 5 library providing D-Bus add-ons for KDE
applications (libKF5DBusAddons.so).  It registers KDE applications on the
D-Bus session bus, provides KDBusService / KDEDModule / KDEInitInterface /
KDBusInterProcessLock helper classes and ships the kquitapp5 console helper.

OHOS-specific adaptations (inherited from the KF5 attica-kf5/5.116.0 recipe
and the KF6 kdbusaddons/6.14.0 recipe):
  - qt5-qtbase/5.15.2.2, NOT qt5-qtbase/5.15.2: the plain 5.15.2 binary is
    configured without -dbus so it provides no Qt5DBus module, while
    kdbusaddons REQUIRES find_package(Qt5DBus).  The .2 variant links
    dbus/1.14.10 and exposes the Qt5DBus component.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on (KDEInstallDirs etc.)
  - conan_cmakedeps_paths.cmake created manually because qt5-qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH.
  - KF_SKIP_PO_PROCESSING=ON: the qt5 archive ships no Qt5LinguistTools
    (lrelease), which ECMPoQmTools requires to compile the poqm/ trees.
  - Qt mkspec compatibility copy: the published qt5-qtbase binary's
    Qt5CoreConfig references <pkg>/../b/mkspecs/linux-clang which is not
    shipped; we copy the package's own mkspecs/linux-clang there (same trick
    as attica-kf5._prepare_qt_mkspec_compat).
  - WITH_X11 / Qt5X11Extras is optional and absent on OHOS, so HAVE_X11=FALSE
    and the qtx11extras code path is compiled out.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Kdbusaddons5Conan(ConanFile):
    name = "kdbusaddons5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - DBus Addons for KDE"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdbusaddons"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5DBus is only provided by the qt5-qtbase/5.15.2.2 DBus variant.
        self.requires("qt5-qtbase/5.15.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # No Qt5LinguistTools on the qt5 archive -> skip po->qm processing.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # No X11 on HarmonyOS PC: keeps HAVE_X11 off so the qtx11extras code
        # path is compiled out.
        tc.variables["WITH_X11"] = "OFF"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # CMake has no Platform/HarmonyOS module, so the SONAME linker flag
        # stays unset; provide it so libKF5DBusAddons.so gets a DT_SONAME
        # (required by the L5 SONAME gate and downstream soname linking).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            self._prepare_qt_mkspec_compat(qt_pkg)
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

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
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF5DBusAddonsConfig.cmake with proper
        # dependency tracking (find_dependency on Qt5DBus). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5DBusAddons"]
