#!/usr/bin/env python3
"""Conan test_package for kfilemetadata 6.28.0.

Verifies that the KF6FileMetaData library can be found via CMake and that
the SimpleExtractionResult / PropertyInfo API is callable (R34: real API
usage, not a print-only stub). Also exercises the installed extractor
plugin discovery via WriterCollection-free core paths.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KfilemetadataTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        # Put every dependency (KF6 packages + qtbase + transitive deps)
        # lib/cmake on the prefix path so find_package(KF6FileMetaData) and
        # its find_dependency(Qt6Core) chain all resolve.
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
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
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
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        # The sandbox LD_LIBRARY_PATH contains an incompatible
        # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
        # which shadows the compatible one; prepend /system/lib64 so the
        # test binary resolves the compatible libc++ first (kconfig
        # 6.26.0 / bluez-qt 6.28.0 precedent).
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # kfilemetadata extractors are discovered via KPluginFactory; the
        # dump/plaintext extractor plugin lives in the package's plugin dir.
        for p in self.dependencies.values():
            if p and p.package_folder:
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(p.package_folder, "plugins")
                )
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kfilemetadata"),
                env="conanrun",
            )
