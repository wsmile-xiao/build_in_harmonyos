#!/usr/bin/env python3
"""Conan test_package for ksanecore — consumer-side verification.

Links the installed KSane::Core target and runs functional assertions on the
public Option / DeviceInformation API that do not require scanner hardware.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KsanecoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("ki18n/6.26.0")
        self.requires("sane-backends/1.2.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        # The installed KSaneCore6Config.cmake chains through
        # find_dependency(Qt6Gui). qtbase uses cmake_find_mode=none, so
        # CMakeDeps does not add its lib/cmake dir; expose every dependency
        # path manually (kxmlgui 6.18.0 test_package precedent).
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
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        env.define("QT_QPA_PLATFORM", "offscreen")
        # CI workers run inside the OHOS sandbox whose LD_LIBRARY_PATH
        # contains an incompatible libc++_shared.so shadowing the compatible
        # one; prepend /system/lib64 so test executables resolve the
        # compatible libc++ first (kconfig 6.26.0 / kcrash 6.26.0 precedent).
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            sdk_llvm_lib = (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                "/ohos/native/llvm/lib"
            )
            if os.path.isdir(sdk_llvm_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ksanecore")
            self.run(bin_path, env="conanrun")
