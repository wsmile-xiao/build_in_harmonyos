#!/usr/bin/env python3
"""Conan recipe for KDE Maui Communicator 4.0.2 on HarmonyOS PC.

communicator is a KDE Maui contacts manager: a Qt6/QML *executable*
application (qt_add_qml_module with NO_PLUGIN, no library artifacts).

OHOS-specific adaptations:
  - Pure executable package: package_info() declares bindirs only, no
    cpp_info.libs (declaring a nonexistent lib makes CMakeDeps generate a
    target pointing at a missing library, which breaks consumers - see
    DRAFT-bambootracker-qt6-executable-conan).
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in the KDE platform list
    (KF6 6.14 chain precedent).
  - The application needs no source patch beyond the capability patches:
    KPeople (patches/0001) is capability-detected via find_package(KF6People
    CONFIG QUIET); when absent the app falls back to enumerating the shared
    vCard directory directly. KContacts and Qt6::Widgets stay hard
    requirements (deep vCard model usage and the non-Android QApplication
    code path, respectively).
  - patches/0002 drops upstream's unused KF6 KIO and MauiKit4 FileBrowsing
    requirements: no source file uses their symbols and the published mauikit
    package ships no FileBrowsing component. The single user
    of FileBrowsing (avatar file dialog in main.qml) switches to
    QtQuick.Dialogs with the same callback(paths) contract.
  - patches/0003 admits HarmonyOS into upstream's elseif(UNIX) desktop branch
    (CMake has no Platform/HarmonyOS module and leaves UNIX unset, so
    find_package(KF6 COMPONENTS Contacts) was silently skipped and the
    KF6::Contacts target never got defined).
  - QT_ADDITIONAL_PACKAGES_PREFIX_PATH points at the qtdeclarative package so
    Qt6Config.cmake resolves the Qml/Quick components (baloo 6.28.0 precedent).
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
  - Upstream ships no test suite (see notes.md NO_UPSTREAM_TESTS); L1
    verification is the test_package offscreen smoke of the installed
    binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class CommunicatorConan(ConanFile):
    name = "communicator"
    version = "4.0.2"
    description = "KDE Maui Communicator - contacts manager (Qt6/QML application)"
    license = "GPL-3.0-or-later"
    homepage = "https://invent.kde.org/maui/communicator"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6: Qml/Quick/QuickControls2 from qtdeclarative; Concurrent/Widgets
        # (QApplication in main.cpp) from qtbase.
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # KF6 6.14.0 family: every KF6 require sits on the same minor so the
        # graph carries one consistent set of exact pins. KIO is deliberately
        # NOT required: upstream lists KF6::KIOCore/KIOGui as pure CMake
        # boilerplate and no source file uses KIO symbols (patches/0002 drops
        # them). The earlier kcontacts/6.18.0 pin additionally conflicted with
        # the kio 6.14 family's exact kcodecs/6.14.0 pin (Conan 2 refuses two
        # exact pins of one package - ci-run-2.log/ci-run-3.log);
        # kcontacts/6.14.0 resolves that conflict at the root.
        self.requires("ki18n/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kservice/6.14.0")
        self.requires("kcontacts/6.14.0")
        # MauiKit4 core controls only: the published package ships no
        # FileBrowsing component, and the app's only user of it (avatar file
        # dialog in main.qml) was switched to QtQuick.Dialogs by patches/0002.
        # 4.0.2.1, not 4.0.2: the re-release enters the UNIX platform branch
        # on OHOS (CMAKE_SYSTEM_NAME=HarmonyOS leaves UNIX unset), so
        # WindowShadow is compiled and its QML type registered - the 4.0.2
        # package broke every consumer's QML load (ci-run-11).
        self.requires("mauikit/4.0.2.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: executable package - static link default.
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        tc.variables["WARNINGS_ARE_ERRORS"] = "OFF"
        # OHOS is not in the KDE platform list.
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # ECM's installed ECMConfig.cmake sets ECM_MODULE_PATH; the
        # CMakeDeps-generated one does not. Set it manually so the KDE cmake
        # modules (KDEInstallDirs, KDECMakeSettings, ECMSetupVersion, ...)
        # required by the top-level CMakeLists.txt are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtdeclarative and qtdeclarative.package_folder:
            # Qt6Config.cmake resolves additional components (Qml/Quick) via
            # QT_ADDITIONAL_PACKAGES_PREFIX_PATH (baloo 6.28.0 / akonadi
            # 25.12.3 precedent). Without it find_package(Qt6 COMPONENTS Qml)
            # only searches the qtbase lib/cmake prefix and fails (ci-run-4).
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = (
                qtdeclarative.package_folder
            )

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually (knotifications
            # 6.26.0 precedent) so Qt6 and every dependency's config dirs land
            # on CMAKE_PREFIX_PATH, making find_package(Qt6 COMPONENTS ...)
            # and the find_package(KF6 COMPONENTS ...) aggregate resolve.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            for dep in self.dependencies.values():
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
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _build_env(self):
        # Qt host tools (rcc/moc/qmlcachegen via qtbase host bin) and
        # dependency shared libraries must be loadable during configure/build.
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        # The sandbox bundle dir ships a libc++_shared.so that can shadow the
        # compatible system one while ECM's ecm_query_qt runs qtpaths; give
        # the system loader dir precedence (kconfig 6.26.0 precedent).
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Pure executable package: declare bindirs only, no cpp_info.libs.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
