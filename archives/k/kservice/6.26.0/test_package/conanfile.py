#!/usr/bin/env python3
"""Conan test_package for kservice 6.26.0.

Verifies that the KF6Service library can be found via CMake and that
constructing a KService and reading its accessors works (R34: real API
usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KserviceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        for dep_name in ("kconfig", "kcoreaddons", "ki18n"):
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
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; CI workers may not export it via
        # LD_LIBRARY_PATH (observed on OpenHarmonyPCDeveloper-CI-021).
        # Prepend it so CMake's TryCompile can link. Must not clobber the
        # conanbuild env on other hosts.
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        env = Environment()
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = Environment()
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        env.define("QT_QPA_PLATFORM", "offscreen")
        # CI workers run inside the OHOS sandbox whose LD_LIBRARY_PATH
        # contains an incompatible libc++_shared.so (under
        # /data/storage/el1/bundle/libs/arm64) shadowing the compatible
        # one; prepend /system/lib64 so test executables resolve the
        # compatible libc++ first (kconfig 6.26.0 / kcrash 6.26.0
        # precedent, same fix as the main recipe).
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            sdk_llvm_lib = (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                "/ohos/native/llvm/lib"
            )
            if os.path.isdir(sdk_llvm_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kservice"),
                env="conanrun",
            )
