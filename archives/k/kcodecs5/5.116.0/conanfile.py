#!/usr/bin/env python3
"""Conan recipe for kcodecs5 5.116.0 on HarmonyOS PC.

kcodecs (KF5/Qt5) is the KDE Frameworks 5 string/text codec library
(libKF5Codecs.so), providing base64, quoted-printable, uuencode, RFC2047
encoded-word and legacy charset handling on top of Qt5Core.

OHOS-specific adaptations (modeled on kcoreaddons5/5.116.0, same KF5/Qt5
baseline):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - CMAKE_SYSTEM_NAME=Linux: CMake 4.1 has no Platform/HarmonyOS module, so
    the `UNIX` variable is not set and KDE's KDECMakeSettings / install-dir
    logic behaves as a non-UNIX platform. OHOS is a POSIX system, so forcing
    the Linux platform is fully compatible (R32-safe: no __OHOS__ macros
    anywhere).
  - KDE_INSTALL_USE_QT_SYS_PATHS=OFF: install into kcodecs5's own prefix,
    not Qt's.
  - ecm_install_po_files_as_qm(poqm) disabled via patches/0001 because
    Qt5LinguistTools is not published to ohpcd.
  - BUILD_TESTING=ON configures the upstream autotests; the 7 upstream
    ctest cases were exercised in the exploratory phase (7/7 pass on the
    OHOS device — Qt5's QTextCodec ships the legacy charsets, so unlike the
    KF6 kcodecs no iconv fallback is needed). The conan build() does NOT
    embed ctest, so the sandbox's execution limits cannot fail conan create;
    results are recorded in reports/test-report.md and test_package/MANIFEST.yml
    honestly declares upstream_test_in_build=false.
  - Dependencies: qt5-qtbase/5.15.2 (Qt5Core), ecm/6.20.0 (ECM)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project's CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Kcodecs5Conan(ConanFile):
    name = "kcodecs5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - KDE Codecs"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcodecs"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        shared = bool(self.options.shared)
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        # See class docstring: CMake 4.1 lacks Platform/HarmonyOS, so the UNIX
        # platform variable is not set. Force the Linux platform so KDE's
        # KDECMakeSettings and install-dir logic behaves as a POSIX build
        # (R32-safe: OHOS is POSIX-compatible, no __OHOS__ macros anywhere).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"

        if str(self.settings.os) == "OHOS":
            # aarch64-linux-ohos target for the OHOS clang toolchain
            targets = {
                "armv8": "aarch64-linux-ohos",
                "x86_64": "x86_64-linux-ohos",
            }
            target = targets.get(str(self.settings.arch))
            if target:
                tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target

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
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
            qt_pkg = qtbase.package_folder.replace("\\", "/")
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder.replace("\\", "/")
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Qt5CoreConfigExtrasMkspecDir.cmake references
        # ${_qt5Core_install_prefix}/../b/mkspecs/linux-clang, which does not
        # exist in the qt5-qtbase conan package layout. Mirror the real
        # mkspecs dir to the expected location (kcoreaddons5 precedent).
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs"
        )
        if os.path.isdir(source) and not os.path.isdir(expected):
            parent, _ = os.path.split(expected)
            os.makedirs(parent, exist_ok=True)
            import shutil

            shutil.copytree(source, expected)

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Codecs"]
        # KF5Codecs depends on Qt5Core; let the installed
        # KF5CodecsConfig.cmake drive the Qt5::Core find_dependency
        # automatically.
        self.cpp_info.requires = []
