#!/usr/bin/env python3
"""Conan recipe for kidletime 6.26.0 on HarmonyOS PC.

kidletime is a KDE Frameworks 6 library that reports idle time of the
session (libKF6IdleTime.so).

OHOS-specific adaptations (mirroring the kcoreaddons 6.26.0 KF6 recipe):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in KDE's supported platform list: Linux/FreeBSD/Windows/macOS)
  - WITH_X11=OFF / WITH_WAYLAND=OFF: the upstream CMakeLists probes X11/XCB
    and Wayland backends; the OHOS artifact repo ships neither x11/xcb
    components nor PlasmaWaylandProtocols, so both backends are disabled.
    The core KF6IdleTime library still builds (Qt6::Core + Qt6::Gui only).
  - C++20 flags (-std=c++20) required by KDE Frameworks 6 codegen headers.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
  - Dependencies: qtbase/6.11.1 (Qt6Gui), ecm/6.26.0 (ECM, tool_require).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KidletimeConan(ConanFile):
    name = "kidletime"
    version = "6.26.0"
    description = "KDE Frameworks 6 - reports idle time of the session"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/frameworks/kidletime"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def build_requirements(self):
        # ECM 6.26.0 satisfies the project's find_package(ECM 6.26.0).
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # kidletime's exported headers require C++20 (KDEFrameworkCompilerSettings
        # uses std::ranges in some code paths); force it via compiler flags.
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        # OHOS is not in KDE's supported platform allowlist.
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # CMake has no Platform/HarmonyOS module, so UNIX and
        # CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG stay unset and CMake would not
        # pass -Wl,-soname. Provide the flag explicitly so libKF6IdleTime.so
        # gets a DT_SONAME + versioned symlink chain (required by the L5
        # SONAME quality gate and by downstream soname-based linking).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # The OHOS artifact repo has no x11/xcb components and no
        # PlasmaWaylandProtocols; disable both optional backends so the core
        # library (Qt6Core + Qt6Gui) builds.
        tc.variables["WITH_X11"] = "OFF"
        tc.variables["WITH_WAYLAND"] = "OFF"
        # QCH (Qt help) documentation is not needed.
        tc.variables["BUILD_QCH"] = "OFF"

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

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
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
        # R32: keep the OHOS platform check open to Linux as well so the
        # recipe behaves identically on both (patches are OHOS-specific but
        # applying them on Linux is a no-op when patches are empty).
        if self.settings.os in ("Linux", "OHOS"):
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # No upstream autotests (kidletime ships an example, not tests);
        # there is no ctest target to run.

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6IdleTimeConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6IdleTime"]
