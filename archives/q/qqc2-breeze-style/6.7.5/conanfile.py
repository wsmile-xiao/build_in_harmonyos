#!/usr/bin/env python3
"""Conan recipe — qqc2-breeze-style 6.7.5 (CMake + ECM)

QQC2 Breeze Style is the KDE Plasma QML style plugin for Qt Quick Controls
2 ("org.kde.breeze"). It provides pure-QML implementations of the Qt Quick
Controls styling API plus a small C++ helper library (BreezeImpl) and a
Kirigami platform theme plugin (org.kde.breeze kirigami platform plugin).

This package has no public C/C++ API: applications consume it at runtime
via the QML style mechanism (QT_QUICK_CONTROLS_STYLE=org.kde.breeze or
QQuickStyle::setStyle("org.kde.breeze")) and the Kirigami platform plugin
import path. The Conan package exports the QML module tree, the
libBreezeImpl helper library and the kirigami platform plugin.

OHOS-specific adaptations (kiconthemes 6.26.0 / kirigami 6.26.0 precedents):
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS is not in KDE's platform list)
  - USE_DBUS=OFF (Qt6 DBus consumers not needed for the style payload)
  - KF_SKIP_PO_PROCESSING=ON (skip translation catalogs)
  - BUILD_TESTING=OFF: the upstream tarball ships no autotests directory
    (autotests live in the git repo CI branch only); upstream test
    coverage is delivered through the test_package consumer which
    instantiates the QML module and the Kirigami platform plugin.
  - ECM_MODULE_PATH set manually (CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project relies on)
  - conan_cmakedeps_paths.cmake written manually (qtbase uses
    cmake_find_mode=none so CMakeDeps does not add its lib/cmake to
    CMAKE_PREFIX_PATH)
  - /system/lib64 prepended to LD_LIBRARY_PATH for configure and the
    test_package CMake.configure (hnp cmake is an OHOS ELF requiring
    libc++_shared.so from /system/lib64 — gtksourceview5 5.22.0
    precedent: "Error relocating cmake: _ZTINSt4__n1..." exit 127)
  - kirigami pinned to 6.26.0: upstream CMakeLists requires
    KF6_MIN_VERSION 6.26 and FindKF6 rejects kirigami 6.18.0's
    KF6KirigamiPlatformConfig.cmake as too old.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Qqc2BreezeStyleConan(ConanFile):
    name = "qqc2-breeze-style"
    version = "6.7.5"
    description = "KDE Plasma QQC2 Breeze style for Qt Quick Controls 2"
    license = "LGPL-2.0-or-later", "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/plasma/qqc2-breeze-style"
    url = "https://download.kde.org/stable/plasma/6.7.5/qqc2-breeze-style-6.7.5.tar.xz"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # Qt6 line: qqc2-breeze-style 6.7.x requires Qt6 >= 6.10 and
        # KF6 >= 6.26 (KirigamiPlatform is pulled through kirigami).
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtshadertools/6.11.1")
        self.requires("kirigami/6.26.0")
        self.requires("kguiaddons/6.26.0")
        self.requires("kconfig/6.26.0")
        self.requires("kcolorscheme/6.26.0")
        self.requires("kiconthemes/6.26.0")

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
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not. Set it manually.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qt_extra = []
        for dep_name in ("qtdeclarative", "qtsvg", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

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
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml"))
        for rel in ("bin", "lib"):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        env.prepend_path("QT_PLUGIN_PATH", os.path.join(self.build_folder, "bin"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one under
            # /system/lib64; prepend it so host tools (moc, qmlcachegen,
            # ecm_query_qt/qtpaths) resolve the compatible libc++ first
            # (kconfig 6.26.0 / bluez-qt 6.28.0 / kiconthemes 6.26.0 precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs QQC2BreezeStyleConfig.cmake for the QML
        # module; consumers pick the style up through the QML import path,
        # not through a CMake target. Use cmake_find_mode=none so the
        # project's own config file is not shadowed.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # libBreezeImpl is an internal helper library that ships with the
        # QML module; declaring it keeps the linker information complete
        # for consumers that link it directly.
        self.cpp_info.libs = ["BreezeImpl"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "qml"))
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml"))
        self.runenv_info.prepend_path("QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins"))
        self.runenv_info.prepend_path("QT_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "plugins"))
