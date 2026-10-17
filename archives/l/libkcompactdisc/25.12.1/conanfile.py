#!/usr/bin/env python3
"""Conan recipe for libkcompactdisc 25.12.1 on HarmonyOS PC.

libkcompactdisc is a KDE Gear library for interfacing with CD-ROM drives
(audio CD playback, CD-ROM control; produces libKCompactDisc6.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_TESTING=OFF to skip upstream tests during Conan build; the upstream
    tests/testkcd.cpp is not registered with ctest anyway (tests/CMakeLists.txt
    has no add_test), see test_package/MANIFEST.yml for the R51 inventory
  - E092 SONAME fix: CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG injected because
    the OHOS-adapted conan maps os=OHOS -> CMAKE_SYSTEM_NAME=HarmonyOS and
    CMake 4.1 lacks Platform/HarmonyOS.cmake, so the Linux platform module
    (which defines the SONAME flag) is never loaded. The project sets
    SOVERSION 5 (libKCompactDisc6.so.5) so the SONAME flag is required.
  - conan_cmakedeps_paths.cmake created manually because qtbase/solid/ki18n/
    phonon4qt6 all use cmake_find_mode=none (KDE-style configs), which
    prevents CMakeDeps from adding their lib/cmake dirs to CMAKE_PREFIX_PATH
    (karchive/solid/phonon4qt6 precedent)
  - alsa-lib paths added to the same file so CMake's FindALSA and the
    CMakeDeps-generated ALSA config (ALSA::ALSA) resolve HAVE_ALSA=1
  - Dependencies: qtbase/6.11.1 (Qt6Core + Qt6DBus), solid/6.26.0 (KF6Solid),
    ki18n/6.26.0 (KF6I18n + gettext), phonon4qt6/4.12.0 (Phonon::phonon4qt6),
    alsa-lib/1.2.16.1 (optional ALSA, enabled), ecm/6.26.0 (ECM, tool)
"""
import os
import time

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KCompactDiscConan(ConanFile):
    name = "libkcompactdisc"
    version = "25.12.1"
    description = "KDE library for interfacing with CD-ROM drives (libKCompactDisc6.so)"
    license = "LGPL-2.0-or-later AND GPL-2.0-or-later"
    homepage = "https://invent.kde.org/multimedia/libkcompactdisc"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("solid/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("phonon4qt6/4.12.0")
        self.requires("alsa-lib/1.2.16.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt6 DBus is not available in the published qtbase OHOS build
        # (FEATURE_dbus=OFF, solid precedent USE_DBUS=OFF). Disable the
        # optional WITH_QTDBUS feature (adaptation patch); the only DBus
        # consumer is the mediamanager URL lookup, which falls back to the
        # raw device path when disabled.
        tc.variables["WITH_QTDBUS"] = "OFF"

        # ── E092 SONAME 修复（同 phonon4qt6 配方）──────────────────
        # os=OHOS → CMAKE_SYSTEM_NAME=HarmonyOS，CMake 4.1 无
        # Platform/HarmonyOS.cmake → Linux 平台模块未加载 → SONAME flag
        # 未定义 → 链接无 -Wl,-soname → L5a/L5c 失败。项目 SOVERSION 5。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME"] = "1"

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

        # qtbase/solid/ki18n/phonon4qt6 use cmake_find_mode=none -> CMakeDeps
        # does not generate conan_cmakedeps_paths.cmake. Create it manually so
        # the toolchain adds their cmake dirs to CMAKE_PREFIX_PATH (karchive
        # precedent). alsa-lib paths are added to the same file so
        # find_package(ALSA) (config mode via CMakeDeps, ALSA::ALSA) resolves.
        lines = []
        deps = ["qtbase", "solid", "ki18n", "phonon4qt6", "alsa-lib"]
        for dep_name in deps:
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
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
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def _build_with_retry(self, cmake, step):
        """Retry a CMake step to ride out intermittent HMDFS symlink EPERM.

        On HarmonyOS PC the HMDFS integrity engine occasionally and
        transiently denies symlink() (E018/E050: "failed to create symbolic
        link ... Permission denied"). CMake's cmake_symlink_library step for
        the SOVERSION'd libKCompactDisc6 is affected. A short settle delay
        plus a resumed run (object files are cached, only link + symlink are
        redone) clears it. A second consecutive failure is re-raised as a
        genuine error.
        """
        for attempt in (1, 2, 3):
            try:
                if step == "build":
                    cmake.build()
                else:
                    cmake.install()
                return
            except Exception:
                if attempt == 3:
                    raise
                self.output.warning(
                    f"cmake.{step}() attempt {attempt} failed "
                    "(likely intermittent HMDFS symlink EPERM); retrying"
                )
                time.sleep(5)

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        self._build_with_retry(cmake, "build")

    def package(self):
        cmake = CMake(self)
        self._build_with_retry(cmake, "install")
        # Note: the upstream VERSION/SOVERSION target properties are dropped
        # (adaptation patch): HMDFS denies symlink() for processes spawned by
        # the conan package manager (E018/E050), which makes CMake's
        # cmake_symlink_library step unrunnable. The E092 soname flag
        # injection still emits DT_SONAME=libKCompactDisc6.so, and a single
        # unversioned file is shipped, so no runtime resolution is lost.

    def package_info(self):
        # The project installs its own KCompactDisc6Config.cmake with proper
        # dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KCompactDisc6"]
