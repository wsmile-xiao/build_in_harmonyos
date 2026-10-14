#!/usr/bin/env python3
"""Conan recipe for kirigami-gallery 26.04.0 on HarmonyOS PC (aarch64-linux-ohos).

kirigami-gallery is the KDE Release Service demo application for the Kirigami
UI framework: a C++ executable (main.cpp + InfoData.cpp) plus ~56 QML files
embedded into the binary via resources.qrc, built with CMake + ECM.

Dependency closure (all published in the ohpcd registry, verified via
`conan download --only-recipe`, R35):
  - qtbase/6.11.1           Qt6Core/Gui/Widgets (+ offscreen QPA plugin)
  - qtdeclarative/6.11.1    Qt6Qml/Quick/QuickControls2 + QML runtime modules
  - qtsvg/6.11.1            Qt6Svg (icons in gallery QML)
  - qtshadertools/6.11.1    qsb host tool required by QtQuick builds
  - kirigami/6.26.0         KF6Kirigami C++ libs + org.kde.kirigami QML modules
  - kitemmodels/6.18.0.1    KF6ItemModels + org.kde.kitemmodels QML modules
  - ecm/6.26.0 (tool)       extra-cmake-modules build helpers

Upstream requires Qt >= 6.0.0 and KF6 >= 6.12.0 (CMakeLists.txt), satisfied
by the published HarmonyOS Qt 6.11.1 chain and Kirigami 6.26.0.

Notes:
  - KF_SKIP_PO_PROCESSING=ON skips ecm_install_poqm_files_as_qm(): the
    ECMPoQmTools module short-circuits on this option (ECMPoQmTools.cmake
    "if (KF_SKIP_PO_PROCESSING) return()"), so no Qt6::LinguistTools
    (qttools) dependency is needed. Same decision as kirigami-addons/1.13.0.
  - The src/android/build.gradle file in the tarball is the Qt APK packaging
    helper and is NOT used on non-Android platforms (ecm_add_android_apk is
    behind `if (ANDROID)`); no source changes were needed for it.
  - No shell environment variables are consumed (R33): compiler and flags
    come from the Conan toolchain; dependency paths are derived from
    self.dependencies package folders only (R49).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KirigamiGalleryConan(ConanFile):
    name = "kirigami-gallery"
    version = "26.04.0"
    description = "KDE Kirigami UI framework showcase application (QML gallery demo)"
    license = ("LGPL-2.0-or-later", "GPL-3.0-or-later")
    homepage = "https://invent.kde.org/graphics/kirigami-gallery"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/kirigami-gallery-26.04.0.tar.xz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtshadertools/6.11.1")
        self.requires("kirigami/6.26.0")
        self.requires("kitemmodels/6.18.0.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # No upstream test suite exists (R51: find -iname "*test*" and
        # grep add_test/enable_testing both empty); consumer validation is
        # provided by test_package/ (see test_package/MANIFEST.yml).
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["ENABLE_QML_PROFILING"] = "OFF"
        # KF platform check rejects non-listed platforms; OHOS is a valid
        # Linux-family target for Qt6 but unknown to the KF6 cmake guards.
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip poqm -> qm translation compilation (needs Qt6::LinguistTools
        # from qttools; ECMPoQmTools.cmake short-circuits on this option).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        # ECM find-modules/kde-modules are not on the default CMAKE_MODULE_PATH
        # in a Conan sandbox; point them at the ecm package tree.
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        # Qt aux packages (qml modules, qsb tool, Svg) live in separate
        # conan packages; let the Qt6 host tooling find them at configure
        # and build time (kirigami-addons/1.13.0 pattern).
        qt_extra = []
        for dep_name in ("qtdeclarative", "qtsvg", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        # CMakeDeps generates per-package config files, but this project
        # consumes Qt6/KF6 through their own relocatable CMake config trees
        # (find_package(Qt6 ... COMPONENTS ...), find_package(KF6 ...)),
        # so expose every dependency package folder on CMAKE_PREFIX_PATH
        # plus the ECM module subdirs on CMAKE_MODULE_PATH.
        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _runtime_env(self, include_build=False):
        """Runtime env for host-side Qt tools (qmlcachegen, qsb) executed on
        this OHOS host during build (kirigami-addons/1.13.0 pattern)."""
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                # Qt host tools (qmltyperegistrar/qmlcachegen/qsb) live in
                # libexec/ next to the Qt libraries they need at runtime.
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml"))
        # The host shell LD_LIBRARY_PATH carries whitespace-padded entries
        # (".../chipset-pub-sdk:         /system/lib64") which the OHOS loader
        # cannot resolve, so Qt host tools fail with "libc++_shared.so not
        # found". Provide clean system library dirs explicitly.
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Runtime consumer environment: the QML UI loads org.kde.kirigami /
        # org.kde.kitemmodels / QtQuick modules from the dependency packages.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin")
                )
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml")
                )
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
