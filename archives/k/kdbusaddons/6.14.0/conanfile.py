#!/usr/bin/env python3
"""Conan recipe for kdbusaddons 6.14.0 on HarmonyOS PC.

kdbusaddons is a KDE Frameworks 6 library providing DBus add-ons for KDE
applications (libKF6DBusAddons.so).  It registers KDE applications on the
D-Bus session bus, provides the KDBusService / KDEDModule / KDBusService
helper classes and ships the kquitapp6 console helper.

OHOS-specific adaptations (inherited from the KF6 6.14.0 recipes, e.g.
kcoreaddons/6.14.0):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - WITH_X11=OFF: HarmonyOS PC has no X11 window system.  This compiles out
    the QX11Info code path in kdbusservice.cpp and avoids linking
    Qt6::GuiPrivate (qtx11extras_p.h).
  - BUILD_TESTING=OFF to skip the upstream CTest suite during the Conan
    build: the upstream autotests need a running D-Bus session bus which is
    not available in the HarmonyOS build environment.
  - Dependencies: qtbase-sql-dbus/6.11.1 (Qt6Core + Qt6DBus; plain
    qtbase/6.11.1 is built with FEATURE_dbus=OFF so it cannot provide the
    Qt6DBus module that kdbusaddons REQUIRES), ecm/6.20.0 (ECM, satisfies
    find_package(ECM 6.14.0))
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase-sql-dbus
    uses cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KdbusaddonsConan(ConanFile):
    name = "kdbusaddons"
    version = "6.14.0"
    description = "KDE Frameworks 6 - KDE DBus Addons"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdbusaddons"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase/6.11.1 is built with FEATURE_dbus=OFF; Qt6DBus is only
        # provided by the qtbase-sql-dbus variant (which additionally links
        # dbus/1.14.10 for the D-Bus C library).
        self.requires("qtbase-sql-dbus/6.11.1")

    def build_requirements(self):
        # kdbusaddons 6.14.0 requires ECM >= 6.14.0; ecm/6.20.0 is the
        # published ECM for the KF6 6.14 series.
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
        # No X11 on HarmonyOS PC: keeps HAVE_X11 off so the qtx11extras_p.h
        # code path is compiled out and Qt6::GuiPrivate is not linked.
        tc.variables["WITH_X11"] = "OFF"
        # CMake has no Platform/HarmonyOS module, so UNIX and
        # CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG stay unset and CMake would not
        # pass -Wl,-soname. Provide the flag explicitly so libKF6DBusAddons.so
        # gets a DT_SONAME + versioned symlink chain (required by the L5
        # SONAME quality gate and by downstream soname-based linking).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase-sql-dbus uses cmake_find_mode=none -> CMakeDeps does not
            # generate conan_cmakedeps_paths.cmake. Create it manually so the
            # toolchain adds qtbase's cmake dirs to CMAKE_PREFIX_PATH, making
            # find_package(Qt6DBus)/find_package(Qt6Gui) and the transitive
            # find_dependency() chains all resolve.
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

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6DBusAddonsConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6DBus). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6DBusAddons"]
