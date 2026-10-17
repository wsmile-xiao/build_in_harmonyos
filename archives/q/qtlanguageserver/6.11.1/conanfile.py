#!/usr/bin/env python3
"""Conan recipe for Qt Language Server 6.11.1."""
import os

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


class QtLanguageServerConan(ConanFile):
    name = "qtlanguageserver"
    version = "6.11.1"
    description = "Qt private libraries for JSON-RPC and Language Server Protocol"
    license = "GPL-2.0-only OR GPL-3.0-only OR LGPL-3.0-only"
    homepage = "https://code.qt.io/cgit/qt/qtlanguageserver.git/"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def requirements(self):
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qtlanguageserver supports Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.fPIC
        if self.settings.os == "OHOS":
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        tc.variables["QT_BUILD_TESTS"] = True
        tc.variables["QT_BUILD_TESTS_BY_DEFAULT"] = True
        tc.variables["QT_BUILD_EXAMPLES"] = False
        tc.variables["QT_BUILD_BENCHMARKS"] = False
        tc.variables["QT_BUILD_MANUAL_TESTS"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" '
                "--output-on-failure -j1",
                env="conanrun",
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
        self.cpp_info.libs = ["Qt6LanguageServer", "Qt6JsonRpc"]
        self.cpp_info.includedirs = [
            "include",
            "include/QtLanguageServer/6.11.1",
            "include/QtJsonRpc/6.11.1",
        ]
        # Qt installs complete CMake package files for these private modules.
        # Reuse them so their dependency remains Qt6::Core; a generated
        # CMakeDeps config incorrectly asks CMake for a non-existent
        # qtbaseConfig.cmake file.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
