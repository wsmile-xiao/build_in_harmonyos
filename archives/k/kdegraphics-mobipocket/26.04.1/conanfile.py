#!/usr/bin/env python3
"""Conan recipe for kdegraphics-mobipocket 26.04.1 on HarmonyOS PC.

kdegraphics-mobipocket is a KDE library for reading Mobipocket format e-books.
It provides the QMobipocket6 shared library (libQMobipocket6.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not in KDE platform list)
  - BUILD_TESTING=OFF to skip upstream tests during Conan build
  - Dependencies: qtbase/6.11.1 (Qt6Core, Qt6Gui), ecm/6.20.0 (Extra CMake Modules)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable that the project's CMakeLists.txt relies on
  - QUERY_EXECUTABLE set to qtpaths6 binary so ECM's ECMQueryQt bypasses
    the Qt6::qtpaths target lookup (Qt6Config.cmake doesn't load Qt6CoreTools)
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KdegraphicsMobipocketConan(ConanFile):
    name = "kdegraphics-mobipocket"
    version = "26.04.1"
    description = "KDE library for reading Mobipocket format e-books"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/graphics/kdegraphics-mobipocket"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

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

        # ECM's ECMQueryQt.cmake calls find_package(Qt6 COMPONENTS CoreTools
        # QUIET CONFIG) and then checks for TARGET Qt6::qtpaths. The
        # CMakeDeps/Qt6Config mechanism may not load Qt6CoreTools properly.
        # Set QUERY_EXECUTABLE and _cli_option directly so ECMQueryQt
        # bypasses the target lookup and uses the qtpaths6 binary.
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            tc.variables["QUERY_EXECUTABLE"] = qtpaths6
            tc.variables["_cli_option"] = "--query"

        tc.generate()

        # qtbase uses cmake_find_mode=none, so CMakeDeps doesn't generate
        # conan_cmakedeps_paths.cmake. When this file is absent, the toolchain
        # falls into an else() block that sets CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH
        # from dependency builddirs. By creating the file manually to add
        # qtbase's lib/cmake, we also cause the toolchain to skip that else()
        # block, so we must replicate ALL the path setup here.
        qtbase = self.dependencies.get("qtbase")
        ecm_dep = self.dependencies.build.get("ecm")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            # qtbase cmake directory (for find_package(Qt6))
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            # qtbase library and include paths
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm_dep:
                ecm_pkg = ecm_dep.package_folder
                # ECM cmake modules directory (for find_package(ECM))
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
                # ECM bin (for qtpaths6 etc.)
                lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm_pkg}/bin")')
            # generators folder
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")'
            )
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own QMobipocket6Config.cmake with proper
        # dependency tracking (find_dependency on Qt6Core and Qt6Gui).
        # Use cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["QMobipocket6"]
