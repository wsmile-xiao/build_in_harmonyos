#!/usr/bin/env python3
"""Conan recipe for sonnet 6.26.0 on HarmonyOS PC.

Sonnet is a KDE Frameworks 6 spell checking library.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection
  - SONNET_USE_QML=OFF: Qt6Quick not published to ohpcd
  - SONNET_NO_BACKENDS=ON: no spell checking backends on OHOS
  - BUILD_TESTING=ON: upstream tests enabled (5/7 pass, 2 UI tests need Qt6Widgets runtime)
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SonnetConan(ConanFile):
    name = "sonnet"
    version = "6.26.0"
    description = "KDE Frameworks 6 spell checking library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/sonnet"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtbase-gui/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["SONNET_USE_WIDGETS"] = "ON"
        tc.variables["SONNET_USE_QML"] = "OFF"
        tc.variables["SONNET_NO_BACKENDS"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip .po -> .qm processing entirely. ECMPoQmTools would otherwise
        # invoke lconvert (from qttools) at build time, and that tool fails to
        # load libQt6Core on this platform ("symbol not found"). The .qm
        # translations are not required for the library to function.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # Build the UI library (SONNET_USE_WIDGETS) but not the Qt Designer
        # plugin; the plugin requires Qt6UiPlugin from the qttools package,
        # which is otherwise unneeded and brings extra runtime deps.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"

        # Set ECM_MODULE_PATH manually
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # KF_SKIP_PO_PROCESSING means ECMPoQmTools early-returns, so neither
        # Qt6LinguistTools nor lconvert is needed; qttools is not a dependency.

        # Ensure qtbase cmake files are found
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()

        # After configure: build-time helper tools (parsetrigrams6/gentrigrams
        # from this project) are Qt6-linked executables that must find the Qt6
        # runtime libraries, otherwise loading them fails with "symbol not
        # found". The build env does not carry those paths, so export them
        # here — os.environ propagates to every child process.
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtb_lib = os.path.join(qtbase.package_folder, "lib")
            if qtb_lib not in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep):
                existing = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = qtb_lib + (os.pathsep + existing if existing else "")

        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6SonnetCore"]
        self.cpp_info.includedirs = [os.path.join("include", "KF6", "SonnetCore")]
