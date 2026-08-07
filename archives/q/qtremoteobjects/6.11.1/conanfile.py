#!/usr/bin/env python3
"""Conan recipe for Qt Remote Objects 6.11.1."""
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


class QtRemoteObjectsConan(ConanFile):
    name = "qtremoteobjects"
    version = "6.11.1"
    description = "Qt inter-process object sharing and replication module"
    license = "GPL-3.0-only OR LGPL-3.0-only OR LicenseRef-Qt-Commercial"
    homepage = "https://doc.qt.io/qt-6/qtremoteobjects-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qtremoteobjects supports Linux and OHOS")

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
        is_ohos = self.settings.os == "OHOS"
        if is_ohos:
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        tc.variables["QT_BUILD_TESTS"] = True
        tc.variables["QT_BUILD_TESTS_BY_DEFAULT"] = False
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
            self.output.info(
                "Running 5 upstream Qt Remote Objects POD test functions "
                "with the Conan runtime environment"
            )
            for target in ("tst_pods", "tst_repc_pods"):
                self.run(
                    f'cmake --build "{self.build_folder}" '
                    f'--config {self.settings.build_type} '
                    f'--target {target} -j1',
                    env="conanrun",
                )
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure '
                '-R "^(tst_pods|tst_repc_pods)$" -j1',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross-building: upstream Qt Remote Objects tests require "
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
        self.cpp_info.libs = ["Qt6RemoteObjects"]
        # Qt installs a complete Qt6RemoteObjectsConfig.cmake which correctly
        # discovers Qt6.  A CMakeDeps-generated wrapper would instead emit
        # find_dependency(qtbase), but qtbase intentionally exposes only its
        # installed Qt6Config.cmake (cmake_find_mode=none).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
