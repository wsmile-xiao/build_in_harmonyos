#!/usr/bin/env python3
"""Conan recipe — QCoro 0.13.0 for HarmonyOS PC.

Upstream builds with CMake and requires Qt6 (Core, plus the optional
Test/Network/DBus features).

ohpcd's qtbase package sets cmake_find_mode=none and ships Qt's own
Qt6Config.cmake inside its package folder, so CMakeDeps emits no usable Qt6
config: this recipe points CMake at that real config directory (same approach
as libaccounts-qt 1.17 in this repo).

Qt6WebSockets/Qt6Quick/Qt6Qml configs are not part of the ohpcd qtbase package,
so those optional QCoro features stay off. The downstream consumer
(kaccounts-integration) only needs QCoro6::Core.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class QCoroConan(ConanFile):
    name = "qcoro"
    version = "0.13.0"
    description = "QCoro — coroutine support library for Qt6 (QCoro6)"
    license = "MIT"
    homepage = "https://github.com/qcoro/qcoro"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Consumers (kaccounts-integration) do find_package(QCoro6 COMPONENTS Core)
        deps.set_property("qcoro", "cmake_file_name", "QCoro6")
        deps.generate()

        tc = CMakeToolchain(self)
        qtbase_folder = self.dependencies["qtbase"].package_folder
        qt6_dir = os.path.join(qtbase_folder, "lib", "cmake", "Qt6")
        if os.path.isdir(qt6_dir):
            tc.variables["Qt6_DIR"] = qt6_dir
            tc.variables["CMAKE_PREFIX_PATH"] = qtbase_folder
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["QCORO_BUILD_EXAMPLES"] = False
        tc.variables["QCORO_BUILD_TESTING"] = False
        tc.variables["QCORO_WITH_QTDBUS"] = True
        tc.variables["QCORO_WITH_QTNETWORK"] = True
        tc.variables["QCORO_WITH_QTTEST"] = True
        tc.variables["QCORO_WITH_QTWEBSOCKETS"] = False
        tc.variables["QCORO_WITH_QTQUICK"] = False
        tc.variables["QCORO_WITH_QML"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "QCoro6")
        self.cpp_info.includedirs = ["include/qcoro6"]
        self.cpp_info.cxxstd = "20"

        # Component targets do not inherit the root cpp_info, so every component
        # declares the include dirs itself. Mirror upstream QCoro6Targets.cmake,
        # which exposes these four dirs (consumers include <QCoro/QCoroTask>).
        # cxxstd is per-component too: QCoro headers need C++20 coroutines.
        for _comp in ("Coro", "Core", "Network", "DBus", "Test"):
            self.cpp_info.components[_comp].includedirs = [
                "include", "include/qcoro6", "include/qcoro6/qcoro", "include/qcoro6/QCoro",
            ]
            self.cpp_info.components[_comp].cxxstd = "20"

        # Upstream ships Coro and Test as INTERFACE (header-only) components:
        # declaring libs for them makes CMakeDeps look for libQCoro6Coro.a /
        # libQCoro6Test.a, which upstream never installs, so find_package fails.
        self.cpp_info.components["Coro"].set_property("cmake_target_name", "QCoro6::Coro")

        self.cpp_info.components["Core"].libs = ["QCoro6Core"]
        self.cpp_info.components["Core"].requires = ["Coro", "qtbase::qtbase"]
        self.cpp_info.components["Core"].set_property("cmake_target_name", "QCoro6::Core")

        self.cpp_info.components["Network"].libs = ["QCoro6Network"]
        self.cpp_info.components["Network"].requires = ["Core"]
        self.cpp_info.components["Network"].set_property("cmake_target_name", "QCoro6::Network")

        self.cpp_info.components["DBus"].libs = ["QCoro6DBus"]
        self.cpp_info.components["DBus"].requires = ["Core"]
        self.cpp_info.components["DBus"].set_property("cmake_target_name", "QCoro6::DBus")

        self.cpp_info.components["Test"].requires = ["Core"]
        self.cpp_info.components["Test"].set_property("cmake_target_name", "QCoro6::Test")
