#!/usr/bin/env python3
"""Conan recipe for Qt WebSockets 6.11.1.1.1 (CMake, OHOS SSL variant).

Built against the qtbase/6.11.1.1.1 SSL variant so libQt6WebSockets.so
exports the QWebSocket SSL API (ignoreSslErrors/setSslConfiguration/
sslErrors/preSharedKeyAuthenticationRequired) required by eID clients such
as AusweisApp.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class QtWebSocketsConan(ConanFile):
    name = "qtwebsockets"
    version = "6.11.1.1.1"
    description = "Qt WebSockets client and server module"
    license = "GPL-3.0-only OR LGPL-3.0-only OR LicenseRef-Qt-Commercial"
    homepage = "https://doc.qt.io/qt-6/qtwebsockets-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OHOS SSL variant: build against qtbase/6.11.1.1.1 (FEATURE_openssl=ON)
        # so the QWebSocket SSL API is compiled into libQt6WebSockets.so.
        self.requires(
            "qtbase/6.11.1.1.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtwebsockets/6.11.1.1.1 in this recipe is a HarmonyOS PC "
                "SSL variant; use qtwebsockets/6.11.1 for other platforms"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        if self.settings.os == "OHOS":
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        tc.variables["QT_BUILD_TESTS"] = True
        tc.variables["QT_BUILD_TESTS_BY_DEFAULT"] = True
        tc.variables["QT_BUILD_EXAMPLES"] = False
        tc.variables["QT_BUILD_EXAMPLES_BY_DEFAULT"] = False
        tc.variables["QT_BUILD_BENCHMARKS"] = False
        tc.variables["QT_BUILD_MANUAL_TESTS"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def _ctest_executable(self):
        for candidate in (
            shutil.which("ctest"),
            "/data/service/hnp/bin/ctest",
            "/data/service/hnp/cmake.org/cmake_4.1.2/bin/ctest",
        ):
            if (
                candidate
                and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)
            ):
                return candidate
        raise ConanInvalidConfiguration("ctest executable was not found")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.output.info(
                "Running configured upstream Qt WebSockets auto tests with "
                "the Conan runtime environment"
            )
            ctest = self._ctest_executable()
            self.run(
                f'"{ctest}" --test-dir "{self.build_folder}" '
                "--output-on-failure -j1",
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross-building: upstream Qt WebSockets tests require "
                "a runnable target"
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["Qt6WebSockets"]
        # Qt installs complete Qt6WebSocketsConfig.cmake files. Reuse them so
        # consumers keep the upstream Qt6::WebSockets target and avoid a
        # generated CMakeDeps config that would search for qtbaseConfig.cmake.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
